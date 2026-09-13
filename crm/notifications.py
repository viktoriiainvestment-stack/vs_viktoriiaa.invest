import os
import requests

TELEGRAM_CRM_BOT_TOKEN = os.environ.get("TELEGRAM_CRM_BOT_TOKEN")
ADMIN_TELEGRAM_CHAT_ID = os.environ.get("ADMIN_TELEGRAM_CHAT_ID")


def notify_admin(text):
    """Push a message to the admin's own Telegram chat.

    Uses the raw Bot API (not the telebot instance) so it works from any
    process — the Telegram bot, the lead webhook, or the daily digest —
    without them importing each other.
    """
    if not TELEGRAM_CRM_BOT_TOKEN or not ADMIN_TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_CRM_BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
    except requests.RequestException:
        pass
