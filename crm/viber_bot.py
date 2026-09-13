import os
import re
import requests

from db import find_by_channel, create_lead, update_lead
from notifications import notify_admin

VIBER_TOKEN = os.environ.get("VIBER_BOT_TOKEN")
VIBER_BOT_NAME = os.environ.get("VIBER_BOT_NAME", "Лійка")
API_URL = "https://chatapi.viber.com/pa"

PHONE_RE = re.compile(r"(\+?\d[\d\s\-\(\)]{7,}\d)")
WELCOME_TEXT = (
    "Вітаємо! Дякуємо за звернення щодо інвестиційної нерухомості 🏡\n"
    "Залиште, будь ласка, номер телефону та кілька слів, що саме цікавить "
    "(бюджет, місто, ціль) — і менеджер зв'яжеться з вами."
)
ACK_TEXT = "Дякуємо, заявку отримано! Менеджер зв'яжеться найближчим часом."


def _headers():
    return {"X-Viber-Auth-Token": VIBER_TOKEN, "Content-Type": "application/json"}


def send_message(receiver_id, text):
    if not VIBER_TOKEN:
        return
    requests.post(
        f"{API_URL}/send_message",
        json={
            "receiver": receiver_id,
            "min_api_version": 7,
            "sender": {"name": VIBER_BOT_NAME},
            "type": "text",
            "text": text,
        },
        headers=_headers(),
        timeout=10,
    )


def register_webhook(public_url):
    """Call once after deploying, with the public HTTPS URL of /viber/webhook."""
    if not VIBER_TOKEN:
        raise RuntimeError("VIBER_BOT_TOKEN is not set")
    resp = requests.post(
        f"{API_URL}/set_webhook",
        json={
            "url": public_url,
            "event_types": ["conversation_started", "message", "unsubscribed"],
        },
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def handle_event(payload):
    event = payload.get("event")

    if event == "conversation_started":
        user = payload.get("user", {})
        external_id = user.get("id", "")
        lead = find_by_channel("viber", external_id)
        if not lead:
            create_lead({
                "name": user.get("name", ""),
                "stage": "cold",
                "channel": "viber",
                "externalId": external_id,
                "notes": "Розпочав діалог у Viber",
            })
            notify_admin(f"🆕 Новий лід (Viber): {user.get('name', external_id)}")
        return {"sender": {"name": VIBER_BOT_NAME}, "type": "text", "text": WELCOME_TEXT}

    if event == "message":
        sender = payload.get("sender", {})
        external_id = sender.get("id", "")
        message = payload.get("message", {})
        text = message.get("text", "") if message.get("type") == "text" else ""

        lead = find_by_channel("viber", external_id)
        phone_match = PHONE_RE.search(text) if text else None

        if not lead:
            lead = create_lead({
                "name": sender.get("name", ""),
                "phone": phone_match.group(1) if phone_match else "",
                "stage": "cold",
                "channel": "viber",
                "externalId": external_id,
                "notes": text,
            })
            notify_admin(f"🆕 Новий лід (Viber): {sender.get('name', external_id)}\n{text}")
        else:
            updates = {}
            if phone_match and not lead.get("phone"):
                updates["phone"] = phone_match.group(1)
            merged_notes = (lead.get("notes") or "")
            if text:
                merged_notes = (merged_notes + "\n" + text).strip()
            updates["notes"] = merged_notes
            update_lead(lead["id"], updates)

        send_message(external_id, ACK_TEXT)
        return {}

    return {}
