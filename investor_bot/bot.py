"""Telegram-бот "аналітик інвестора": приймає сайти забудовників, файли й
нотатки від менеджера проекту, складає по них аналіз, складає копію всього
в Google Диск (папка "Ринок" -> підпапка проекту) і відповідає на конкретні
питання з посиланням на джерело. Див. investor_bot/README.md для запуску.
"""
import os
import re

import telebot
from telebot import types

import analysis
import db
import drive
import extract

TOKEN = os.environ.get("TELEGRAM_INVESTOR_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN) if TOKEN else None

MAX_FILE_BYTES = 19 * 1024 * 1024  # ліміт Telegram Bot API на завантаження файлу

URL_RE = re.compile(r"https?://\S+")
QUESTION_STARTERS = (
    "яка", "який", "яке", "які", "яку", "яких", "скільки", "де", "чи",
    "коли", "покажи", "знайди", "порахуй", "назви", "що", "хто", "як",
    "розкажи", "поясни",
)

WELCOME = (
    "Привіт! Я аналізую інвестиційні пропозиції по нерухомості.\n\n"
    "1. Створіть проект: /project Назва готелю чи ЖК\n"
    "2. Скидайте мені все по ньому — сайт забудовника (просто вставте "
    "посилання), презентації, фінмодель у Excel, договори, фото — я "
    "проаналізую кожен матеріал і складу копію в Google Диск, у папку "
    "«Ринок»/назва проекту.\n"
    "3. Питайте що завгодно по проекту звичайним текстом (наприклад: "
    "«яка орендна ставка в фінмоделі для готелю?») — відповім і вкажу, "
    "з якого документа взяв інформацію.\n"
    "4. /analyze — зведений інвестиційний аналіз по всіх матеріалах проекту.\n\n"
    "/projects — список проектів, /use Назва — перемкнутись, /status — "
    "що зараз активне."
)


def _looks_like_question(text):
    stripped = text.strip()
    if stripped.endswith("?"):
        return True
    first_word = stripped.lower().split(" ", 1)[0].strip(",.!") if stripped else ""
    return first_word in QUESTION_STARTERS


def _require_project(chat_id):
    project = db.get_active_project(chat_id)
    return project


def _upload_material_file(project, filename, data, mime_type):
    if not drive.is_configured():
        return None
    folder = drive.project_folder(project["name"])
    if not folder:
        return None
    if not project["drive_folder_id"]:
        conn = db.get_conn()
        conn.execute(
            "UPDATE projects SET drive_folder_id = ?, drive_folder_link = ? WHERE id = ?",
            (folder["id"], folder.get("webViewLink", ""), project["id"]),
        )
        conn.commit()
        conn.close()
    return drive.upload_bytes(folder["id"], filename, data, mime_type)


if bot:

    @bot.message_handler(commands=["start", "help"])
    def handle_start(message):
        bot.send_message(message.chat.id, WELCOME)

    @bot.message_handler(commands=["project", "new"])
    def handle_project(message):
        chat_id = message.chat.id
        name = message.text.split(" ", 1)[1].strip() if " " in message.text else ""
        if not name:
            bot.reply_to(message, "Вкажіть назву: /project Назва проекту")
            return
        project = db.find_project_by_name(chat_id, name)
        if not project:
            project = db.create_project(chat_id, name)
        db.set_active_project(chat_id, project["id"])
        reply = f"Активний проект: «{project['name']}»."
        if drive.is_configured():
            folder = drive.project_folder(project["name"])
            if folder:
                conn = db.get_conn()
                conn.execute(
                    "UPDATE projects SET drive_folder_id = ?, drive_folder_link = ? WHERE id = ?",
                    (folder["id"], folder.get("webViewLink", ""), project["id"]),
                )
                conn.commit()
                conn.close()
                reply += f"\nПапка на Диску: {folder.get('webViewLink', '(створено)')}"
        else:
            reply += "\n(Google Диск не налаштовано — матеріали зберігаються лише в базі бота.)"
        bot.reply_to(message, reply)

    @bot.message_handler(commands=["projects"])
    def handle_projects(message):
        projects = db.list_projects(message.chat.id)
        if not projects:
            bot.reply_to(message, "Поки немає жодного проекту. Створіть: /project Назва")
            return
        active = db.get_active_project(message.chat.id)
        lines = []
        for p in projects:
            mark = "➡️ " if active and active["id"] == p["id"] else "• "
            lines.append(f"{mark}{p['name']}")
        bot.reply_to(message, "Ваші проекти:\n" + "\n".join(lines) + "\n\nПеремкнутись: /use Назва")

    @bot.message_handler(commands=["use"])
    def handle_use(message):
        chat_id = message.chat.id
        name = message.text.split(" ", 1)[1].strip() if " " in message.text else ""
        project = db.find_project_by_name(chat_id, name) if name else None
        if not project:
            bot.reply_to(message, "Не знайшов такого проекту. Список: /projects")
            return
        db.set_active_project(chat_id, project["id"])
        bot.reply_to(message, f"Активний проект: «{project['name']}».")

    @bot.message_handler(commands=["status"])
    def handle_status(message):
        project = _require_project(message.chat.id)
        if not project:
            bot.reply_to(message, "Активного проекту немає. Створіть: /project Назва")
            return
        materials = db.list_materials(project["id"])
        lines = [f"Проект: «{project['name']}»", f"Матеріалів: {len(materials)}"]
        for m in materials[-15:]:
            lines.append(f"  • {m['title']} ({m['kind']})")
        if project["drive_folder_link"]:
            lines.append(f"Папка на Диску: {project['drive_folder_link']}")
        bot.reply_to(message, "\n".join(lines))

    @bot.message_handler(commands=["analyze"])
    def handle_analyze(message):
        project = _require_project(message.chat.id)
        if not project:
            bot.reply_to(message, "Активного проекту немає. Створіть: /project Назва")
            return
        materials = db.list_materials(project["id"])
        if not materials:
            bot.reply_to(message, "У проекті ще немає матеріалів — надішліть сайт, файли чи нотатки.")
            return
        bot.reply_to(message, "Аналізую всі матеріали проекту, зачекайте...")
        chunks = db.list_chunks(project["id"])
        by_material = {}
        for c in chunks:
            by_material.setdefault(c["material_id"], []).append(c["text"])
        materials_with_text = []
        for m in materials:
            text = "\n".join(by_material.get(m["id"], []))
            if text:
                materials_with_text.append({"title": m["title"], "kind": m["kind"], "text": text})
        if not materials_with_text:
            bot.reply_to(message, "З наявних матеріалів не вдалось дістати текст для аналізу.")
            return
        try:
            report = analysis.full_report(project["name"], materials_with_text)
        except Exception as e:
            bot.reply_to(message, f"Не вдалось скласти аналіз: {e}")
            return
        bot.send_message(message.chat.id, report)

    @bot.message_handler(commands=["ask"])
    def handle_ask(message):
        question = message.text.split(" ", 1)[1].strip() if " " in message.text else ""
        if not question:
            bot.reply_to(message, "Напишіть питання після команди: /ask яка орендна ставка в фінмоделі?")
            return
        _answer_question(message, question)

    def _answer_question(message, question):
        project = _require_project(message.chat.id)
        if not project:
            bot.reply_to(message, "Активного проекту немає. Створіть: /project Назва")
            return
        try:
            chunks = analysis.select_relevant(project["id"], question, db)
            answer = analysis.answer_question(project["name"], question, chunks)
        except Exception as e:
            bot.reply_to(message, f"Не вдалось відповісти: {e}")
            return
        bot.reply_to(message, answer)

    def _store_and_report(message, project, kind, title, chunks, source_url="", drive_file=None):
        material = db.add_material(
            project["id"], kind, title, source_url=source_url,
            drive_file_id=(drive_file or {}).get("id", ""),
            drive_file_link=(drive_file or {}).get("webViewLink", ""),
        )
        db.add_chunks(material["id"], project["id"], chunks)
        full_text = "\n".join(text for _, text in chunks)
        reply_parts = []
        if full_text.strip():
            try:
                reply_parts.append(analysis.quick_take(project["name"], title, full_text))
            except Exception as e:
                reply_parts.append(f"(не вдалось згенерувати швидкий аналіз: {e})")
        else:
            reply_parts.append("Додав до проекту, але текст із файлу дістати не вдалось — збережено як є.")
        if drive_file and drive_file.get("webViewLink"):
            reply_parts.append(f"На Диску: {drive_file['webViewLink']}")
        elif drive.is_configured():
            reply_parts.append("(Не вдалось завантажити файл на Google Диск.)")
        bot.reply_to(message, "\n\n".join(reply_parts))

    @bot.message_handler(content_types=["document"])
    def handle_document(message):
        project = _require_project(message.chat.id)
        if not project:
            bot.reply_to(message, "Спершу створіть проект: /project Назва, тоді надсилайте файли.")
            return
        doc = message.document
        if doc.file_size and doc.file_size > MAX_FILE_BYTES:
            bot.reply_to(message, "Файл завеликий (>19 МБ) — надішліть, будь ласка, меншу версію.")
            return
        bot.reply_to(message, f"Отримав «{doc.file_name}», обробляю...")
        try:
            file_info = bot.get_file(doc.file_id)
            data = bot.download_file(file_info.file_path)
        except Exception as e:
            bot.reply_to(message, f"Не вдалось завантажити файл: {e}")
            return

        kind, chunks = extract.extract_file(doc.file_name, data)
        drive_file = None
        try:
            drive_file = _upload_material_file(project, doc.file_name, data, doc.mime_type or "application/octet-stream")
        except Exception as e:
            bot.send_message(message.chat.id, f"(Диск: не вдалось завантажити файл — {e})")

        _store_and_report(message, project, kind or "file", doc.file_name, chunks, drive_file=drive_file)

    @bot.message_handler(content_types=["photo"])
    def handle_photo(message):
        project = _require_project(message.chat.id)
        if not project:
            bot.reply_to(message, "Спершу створіть проект: /project Назва, тоді надсилайте фото.")
            return
        bot.reply_to(message, "Отримав зображення, дивлюсь що на ньому...")
        photo = message.photo[-1]
        try:
            file_info = bot.get_file(photo.file_id)
            data = bot.download_file(file_info.file_path)
        except Exception as e:
            bot.reply_to(message, f"Не вдалось завантажити зображення: {e}")
            return

        filename = f"photo_{photo.file_unique_id}.jpg"
        try:
            description = extract.describe_image(data, "image/jpeg", filename)
            chunks = [("опис зображення", description)]
        except Exception as e:
            chunks = []
            bot.send_message(message.chat.id, f"(не вдалось розпізнати зображення: {e})")

        drive_file = None
        try:
            drive_file = _upload_material_file(project, filename, data, "image/jpeg")
        except Exception as e:
            bot.send_message(message.chat.id, f"(Диск: не вдалось завантажити файл — {e})")

        title = (message.caption or filename).strip()
        _store_and_report(message, project, "image", title, chunks, drive_file=drive_file)

    @bot.message_handler(func=lambda m: True, content_types=["text"])
    def handle_text(message):
        text = message.text.strip()
        if text.startswith("/"):
            return  # невідома команда — ігноруємо мовчки
        project = _require_project(message.chat.id)

        urls = URL_RE.findall(text)
        if urls:
            if not project:
                bot.reply_to(message, "Спершу створіть проект: /project Назва, тоді скидайте посилання.")
                return
            for url in urls:
                bot.reply_to(message, f"Відкриваю {url} ...")
                try:
                    title, chunks = extract.extract_url(url)
                except Exception as e:
                    bot.reply_to(message, f"Не вдалось опрацювати посилання: {e}")
                    continue
                _store_and_report(message, project, "link", title or url, chunks, source_url=url)
            return

        if project and _looks_like_question(text):
            _answer_question(message, text)
            return

        if not project:
            bot.reply_to(message, "Активного проекту немає. Створіть: /project Назва")
            return

        # Звичайний текст без посилань і не схожий на питання — трактуємо
        # як нотатку від менеджера проекту й додаємо до матеріалів.
        parts = extract.chunk_text(text)
        chunks = [(f"частина {i}" if len(parts) > 1 else "нотатка", part) for i, part in enumerate(parts, start=1)]
        title = f"Нотатка від {(message.from_user.full_name or 'інвестора')}"
        drive_file = None
        try:
            drive_file = _upload_material_file(project, f"note_{message.message_id}.txt", text.encode("utf-8"), "text/plain")
        except Exception as e:
            bot.send_message(message.chat.id, f"(Диск: не вдалось завантажити нотатку — {e})")
        _store_and_report(message, project, "text", title, chunks, drive_file=drive_file)


def start_polling():
    if not bot:
        print("TELEGRAM_INVESTOR_BOT_TOKEN не задано — інвест-бот вимкнено.")
        return
    db.init_db()
    print("Інвест-бот запущено...")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    start_polling()
