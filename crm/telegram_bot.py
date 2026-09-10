import os
import re

import telebot
from telebot import types

from db import find_by_external_id, create_lead, update_lead
from notifications import notify_admin

TOKEN = os.environ.get("TELEGRAM_CRM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN) if TOKEN else None

PHONE_RE = re.compile(r"(\+?\d[\d\s\-\(\)]{7,}\d)")

WELCOME = (
    "Вітаємо! Дякуємо за звернення щодо інвестиційної нерухомості 🏡\n"
    "Поділіться, будь ласка, номером телефону кнопкою нижче — і менеджер "
    "зв'яжеться з вами. Або просто напишіть, що саме цікавить."
)
ACK = "Дякуємо, заявку отримано! Менеджер зв'яжеться найближчим часом."


def _contact_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📱 Поділитись контактом", request_contact=True))
    return kb


def send_message(chat_id, text):
    """Used both for admin-picked scripts and for proactive outbound texts."""
    if bot:
        bot.send_message(chat_id, text)


if bot:

    @bot.message_handler(commands=["start"])
    def handle_start(message):
        chat_id = str(message.chat.id)
        lead = find_by_external_id("telegram", chat_id)
        if not lead:
            create_lead({
                "name": message.from_user.full_name or "",
                "stage": "cold",
                "source": "telegram",
                "external_id": chat_id,
                "notes": "Розпочав діалог у Telegram",
            })
            notify_admin(f"🆕 Новий лід (Telegram): {message.from_user.full_name or chat_id}")
        bot.send_message(chat_id, WELCOME, reply_markup=_contact_keyboard())

    @bot.message_handler(commands=["id"])
    def handle_id(message):
        # Lets the admin grab their own chat_id once, to put in ADMIN_TELEGRAM_CHAT_ID.
        bot.send_message(message.chat.id, f"Ваш chat_id: {message.chat.id}")

    @bot.message_handler(content_types=["contact"])
    def handle_contact(message):
        chat_id = str(message.chat.id)
        phone = message.contact.phone_number
        name = f"{message.contact.first_name or ''} {message.contact.last_name or ''}".strip()
        lead = find_by_external_id("telegram", chat_id)
        if lead:
            update_lead(lead["id"], {"phone": phone, "name": name or lead.get("name", "")})
        else:
            create_lead({
                "name": name, "phone": phone, "stage": "cold",
                "source": "telegram", "external_id": chat_id,
            })
            notify_admin(f"🆕 Новий лід (Telegram): {name}, {phone}")
        bot.send_message(chat_id, ACK, reply_markup=types.ReplyKeyboardRemove())

    @bot.message_handler(func=lambda m: True, content_types=["text"])
    def handle_text(message):
        chat_id = str(message.chat.id)
        text = message.text
        phone_match = PHONE_RE.search(text)
        lead = find_by_external_id("telegram", chat_id)
        if not lead:
            create_lead({
                "name": message.from_user.full_name or "",
                "phone": phone_match.group(1) if phone_match else "",
                "stage": "cold", "source": "telegram", "external_id": chat_id,
                "notes": text,
            })
            notify_admin(f"🆕 Новий лід (Telegram): {message.from_user.full_name or chat_id}\n{text}")
        else:
            updates = {"notes": ((lead.get("notes") or "") + "\n" + text).strip()}
            if phone_match and not lead.get("phone"):
                updates["phone"] = phone_match.group(1)
            update_lead(lead["id"], updates)
        bot.send_message(chat_id, ACK)


def start_polling():
    if not bot:
        print("TELEGRAM_CRM_BOT_TOKEN не задано — CRM-бот Telegram вимкнено.")
        return
    bot.infinity_polling(skip_pending=True)
