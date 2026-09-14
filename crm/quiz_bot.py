"""Окремий Telegram-бот — заміна платного блоку SendPulse.

Проводить того самого клієнта через ті самі кваліфікаційні питання
(регіон -> країна, якщо закордон -> готовність чекати будівництво ->
формат інвестування -> термін угоди), показує картку(и) відповідного
проекту, забирає телефон і зручний час дзвінка, і одразу пише лід у
CRM (db.create_lead) — без SendPulse, без вебхука, без оплати.

Тексти питань і карток винесені в crm/quiz_data.py — саме той файл
варто редагувати, коли міняється контент. Тут — тільки механіка.
"""
import os
import time
import traceback
from datetime import date, timedelta
from pathlib import Path

import telebot
from telebot import types

import quiz_data as qd
from db import create_lead
from notifications import notify_admin

TOKEN = os.environ.get("QUIZ_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN) if TOKEN else None

CRM_DIR = Path(__file__).parent

# Стан кожного чату тримаємо в пам'яті процесу — це нормально для
# короткого лінійного квізу (кілька хвилин), не потребує окремої
# таблиці в базі. chat_id -> {"step": int, "answers": {...}}
_sessions = {}

# Порядок кроків. Крок "country" не в QUESTIONS (див. quiz_data.py) —
# вставляємо його вручну одразу після region, і тільки якщо треба.
_BASE_STEPS = list(qd.QUESTIONS)


def _step_for(session):
    """Повертає (question_dict | None, is_country_step: bool)."""
    idx = session["step"]
    answers = session["answers"]

    # Крок 0 — регіон (завжди перший, з qd.QUESTIONS[0]).
    if idx == 0:
        return qd.Q_REGION, False

    # Після регіону: якщо обрали "abroad" і країну ще не питали — питаємо.
    if idx == 1 and answers.get("region") == "abroad" and "country" not in answers:
        return qd.Q_COUNTRY, True

    # Рахуємо, скільки "базових" питань (region, construction, format,
    # timing) уже позаду, компенсуючи вставлений крок country.
    base_idx = idx if not (answers.get("region") == "abroad") else idx - 1
    if 0 <= base_idx < len(_BASE_STEPS):
        return _BASE_STEPS[base_idx], False

    return None, False


def _keyboard_for(question):
    kb = types.InlineKeyboardMarkup()
    for label, value in question["options"]:
        kb.add(types.InlineKeyboardButton(label, callback_data=f"{question['key']}:{value}"))
    return kb


def _contact_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📱 Поділитись контактом", request_contact=True))
    return kb


def _call_time_keyboard():
    """Швидкі кнопки під ASK_TIMING_CALL_TEXT. Клієнт все одно може
    просто написати свій час текстом — handle_text це теж приймає."""
    kb = types.InlineKeyboardMarkup()
    for label, value in qd.CALL_TIME_OPTIONS:
        kb.add(types.InlineKeyboardButton(label, callback_data=f"calltime:{value}"))
    return kb


def _send_question(chat_id, question):
    bot.send_message(chat_id, question["text"], reply_markup=_keyboard_for(question))


def send_message(chat_id, text):
    """Для ручного «Надіслати» й автонадсилання (channel == "quiz_bot") —
    дзвонить сюди, бо лід писав саме цьому боту, і тільки цей бот
    (з тим самим QUIZ_BOT_TOKEN) має з ним «відкритий діалог»."""
    if bot:
        bot.send_message(chat_id, text)


PLACEHOLDER_IMAGE = CRM_DIR / "assets" / "placeholder.jpg"


def _card_image_path(card):
    """Файл фото для картки — її власне, або спільна заглушка, якщо
    "image" не задано чи файл зник. Завжди фото (ніколи None), щоб
    гортання стрілочками (edit_message_media) працювало однаково для
    будь-якої картки — Telegram не дає перетворити повідомлення-фото
    на текстове через edit, тож усі картки мають бути "фото"."""
    image_path = card.get("image") and CRM_DIR / card["image"]
    return image_path if image_path and image_path.is_file() else PLACEHOLDER_IMAGE


def _card_keyboard(index, total):
    kb = types.InlineKeyboardMarkup()
    if total > 1:
        kb.row(
            types.InlineKeyboardButton("◀", callback_data="cardnav:prev"),
            types.InlineKeyboardButton(f"{index + 1}/{total}", callback_data="cardnav:noop"),
            types.InlineKeyboardButton("▶", callback_data="cardnav:next"),
        )
    return kb


def _send_card_carousel(chat_id, session, cards):
    """Одне повідомлення-фото на всі підходящі картки замість купи
    окремих — гортається стрілочками ◀/▶ (handle_card_nav нижче)."""
    with open(_card_image_path(cards[0]), "rb") as photo:
        msg = bot.send_photo(chat_id, photo, caption=cards[0]["text"], reply_markup=_card_keyboard(0, len(cards)))
    session["carousel"] = {"cards": cards, "index": 0, "message_id": msg.message_id}


def _send_cards_and_ask_phone(chat_id, session):
    answers = session["answers"]
    if answers.get("region") == "abroad":
        bot.send_message(chat_id, qd.ABROAD_FALLBACK_TEXT)
    else:
        matched = [c for c in qd.UKRAINE_CARDS if qd.card_matches(c, answers)]
        if matched:
            _send_card_carousel(chat_id, session, matched)
        elif answers.get("construction") == "ready":
            bot.send_message(chat_id, qd.READY_FALLBACK_TEXT)
        else:
            bot.send_message(chat_id, qd.NO_MATCH_FALLBACK_TEXT)
    session["step"] = "awaiting_phone"
    bot.send_message(chat_id, qd.ASK_PHONE_TEXT, reply_markup=_contact_keyboard())


def _next_action_for(timing):
    """(nextActionAt, nextAction) для дашборду CRM за відповіддю на Q_TIMING.

    "Найближчим часом" -> нагадування на сьогодні (одразу у "Задачах"),
    "waiting_exit" -> через ~90 днів, "end_of_year" -> ближче до кінця
    поточного року. "analyzing" і невідомі відповіді — без нагадування,
    ("", "") — лід і так видно в "Нових лідах".
    """
    days = qd.TIMING_FOLLOWUP_DAYS.get(timing)
    label = next((lbl for lbl, val in qd.Q_TIMING["options"] if val == timing), timing)
    if timing == "end_of_year":
        today = date.today()
        target = date(today.year, 12, 20)
        if target < today:
            target = date(today.year + 1, 12, 20)
        return target.isoformat(), f"Зателефонувати — квіз: {label}"
    if days is None:
        return "", ""
    return (date.today() + timedelta(days=days)).isoformat(), f"Зателефонувати — квіз: {label}"


def _finalize_lead(chat_id, session, call_time_label, fallback_name=""):
    """Записує лід у CRM і завершує квіз — спільна для кнопки швидкого
    часу (handle_call_time) і вільного тексту (handle_text)."""
    answers = session["answers"]
    notes = "Пройшов квіз «Підібрати проект»:\n" + _answers_summary(answers)
    notes += f"\nЗручний час дзвінка: {call_time_label}"
    next_action_at, next_action = _next_action_for(answers.get("timing"))

    lead = create_lead({
        "name": session.get("name") or fallback_name,
        "phone": session.get("phone", ""),
        "stage": "cold",
        "leadSource": "quiz",
        "channel": "quiz_bot",
        "externalId": str(chat_id),
        "notes": notes,
        "nextAction": next_action,
        "nextActionAt": next_action_at,
    })
    notify_admin(f"🆕 Новий лід (квіз): {lead['name'] or lead['phone']}")
    bot.send_message(chat_id, qd.THANK_YOU_TEXT)
    del _sessions[chat_id]


def _answers_summary(answers):
    labels = {
        "region": dict(qd.Q_REGION["options"]),
        "country": dict(qd.Q_COUNTRY["options"]),
        "construction": dict(qd.Q_CONSTRUCTION["options"]),
        "format": dict(qd.Q_FORMAT["options"]),
        "timing": dict(qd.Q_TIMING["options"]),
    }
    # invert value->label per question so we can print human text
    lines = []
    for key, question in (
        ("region", qd.Q_REGION), ("country", qd.Q_COUNTRY),
        ("construction", qd.Q_CONSTRUCTION), ("format", qd.Q_FORMAT),
        ("timing", qd.Q_TIMING),
    ):
        value = answers.get(key)
        if value is None:
            continue
        label = next((lbl for lbl, val in question["options"] if val == value), value)
        lines.append(f"— {label}")
    return "\n".join(lines)


if bot:

    @bot.message_handler(commands=["start"])
    def handle_start(message):
        chat_id = message.chat.id
        _sessions[chat_id] = {"step": 0, "answers": {}}
        bot.send_message(chat_id, qd.INTRO_TEXT)
        _send_question(chat_id, qd.Q_REGION)

    @bot.message_handler(commands=["id"])
    def handle_id(message):
        # Дозволяє адміну дізнатись свій chat_id для ADMIN_TELEGRAM_CHAT_ID.
        bot.send_message(message.chat.id, f"Ваш chat_id: {message.chat.id}")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("cardnav:"))
    def handle_card_nav(call):
        chat_id = call.message.chat.id
        session = _sessions.get(chat_id)
        carousel = session and session.get("carousel")
        direction = call.data.split(":", 1)[1]
        if not carousel or direction == "noop":
            bot.answer_callback_query(call.id)
            return

        cards = carousel["cards"]
        step = 1 if direction == "next" else -1
        carousel["index"] = (carousel["index"] + step) % len(cards)
        card = cards[carousel["index"]]
        try:
            with open(_card_image_path(card), "rb") as photo:
                media = types.InputMediaPhoto(photo, caption=card["text"])
                bot.edit_message_media(
                    media, chat_id, call.message.message_id,
                    reply_markup=_card_keyboard(carousel["index"], len(cards)),
                )
            bot.answer_callback_query(call.id)
        except Exception:
            print("Не вдалось погортати картки:", flush=True)
            traceback.print_exc()
            bot.answer_callback_query(call.id, "Не вдалось оновити картку, спробуйте ще раз")

    @bot.callback_query_handler(func=lambda c: not c.data.startswith(("cardnav:", "calltime:")))
    def handle_answer(call):
        chat_id = call.message.chat.id
        session = _sessions.get(chat_id)
        if not session or not isinstance(session.get("step"), int):
            bot.answer_callback_query(call.id, "Почніть заново командою /start")
            return

        key, value = call.data.split(":", 1)
        session["answers"][key] = value
        bot.answer_callback_query(call.id)

        session["step"] += 1
        question, _ = _step_for(session)
        if question:
            _send_question(chat_id, question)
        else:
            _send_cards_and_ask_phone(chat_id, session)

    @bot.message_handler(content_types=["contact"])
    def handle_contact(message):
        chat_id = message.chat.id
        session = _sessions.get(chat_id)
        if not session or session.get("step") != "awaiting_phone":
            # Сесія живе тільки в пам'яті процесу — при кожному деплої
            # (перезапуску бота) вона губиться. Без цього повідомлення
            # людина тисне "Поділитись контактом" у порожнечу й не
            # розуміє, чому бот "мовчить" (саме так і сталось 2026-09-14).
            bot.send_message(
                chat_id,
                "Сесію квізу загублено (можливо, бот саме оновлювався) — "
                "почніть, будь ласка, заново: /start",
                reply_markup=types.ReplyKeyboardRemove(),
            )
            return
        session["phone"] = message.contact.phone_number
        session["name"] = f"{message.contact.first_name or ''} {message.contact.last_name or ''}".strip()
        session["step"] = "awaiting_time"
        bot.send_message(chat_id, qd.ASK_TIMING_CALL_TEXT, reply_markup=_call_time_keyboard())

    @bot.callback_query_handler(func=lambda c: c.data.startswith("calltime:"))
    def handle_call_time(call):
        chat_id = call.message.chat.id
        session = _sessions.get(chat_id)
        if not session or session.get("step") != "awaiting_time":
            bot.answer_callback_query(call.id, "Почніть заново командою /start")
            return
        value = call.data.split(":", 1)[1]
        label = next((lbl for lbl, val in qd.CALL_TIME_OPTIONS if val == value), value)
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"Обрано: {label}")
        _finalize_lead(chat_id, session, label, fallback_name=call.from_user.full_name or "")

    @bot.message_handler(func=lambda m: True, content_types=["text"])
    def handle_text(message):
        chat_id = message.chat.id
        session = _sessions.get(chat_id)
        if not session:
            bot.send_message(chat_id, "Щоб підібрати проєкт, напишіть /start")
            return
        if session.get("step") == "awaiting_phone":
            bot.send_message(chat_id, "Натисніть, будь ласка, кнопку «📱 Поділитись контактом» нижче 👇")
            return
        if session.get("step") != "awaiting_time":
            return  # мід-квізу очікуємо натискання кнопки під питанням, а не текст — ігноруємо мовчки

        # Клієнт написав свій час текстом замість кнопки — теж приймаємо.
        _finalize_lead(chat_id, session, message.text, fallback_name=message.from_user.full_name or "")


def start_polling():
    if not bot:
        print("QUIZ_BOT_TOKEN не задано — квіз-бот вимкнено.", flush=True)
        return
    # Явно друкуємо старт і будь-яку помилку з flush=True: без цього
    # print() під gunicorn на Railway може не долетіти в Deploy Logs
    # (буферизація stdout), і бот виглядає "мовчазним", хоча насправді
    # впав з помилкою (наприклад, невалідний токен).
    print(f"Квіз-бот стартує (токен закінчується на ...{TOKEN[-4:]})", flush=True)
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception:
            print("Квіз-бот впав з помилкою:", flush=True)
            traceback.print_exc()
            time.sleep(5)
