"""Facebook / Instagram Lead Ads -> CRM.

Meta's leadgen webhook only tells us a lead was submitted (leadgen_id,
form_id, page_id) — the actual answers (name, phone, email, custom
questions) have to be fetched separately from the Graph API with the
page's access token. See crm/README.md for how to obtain the app
secret, verify token and page access token, and how to point Meta's
webhook subscription at /meta/webhook.
"""
import hashlib
import hmac
import os

import requests

from db import find_by_channel, create_lead
from notifications import notify_admin

META_APP_SECRET = os.environ.get("META_APP_SECRET")
META_VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN")
META_PAGE_ACCESS_TOKEN = os.environ.get("META_PAGE_ACCESS_TOKEN")
META_GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v21.0")

NAME_KEYS = {"full_name", "name", "first_name"}
PHONE_KEYS = {"phone_number", "phone"}
EMAIL_KEYS = {"email"}


def verify_signature(raw_body: bytes, signature_header: str) -> bool:
    """Checks Meta's X-Hub-Signature-256 header against the app secret,
    so a stranger can't POST fake leads into the CRM."""
    if not META_APP_SECRET or not signature_header:
        return False
    expected = "sha256=" + hmac.new(META_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def fetch_lead_fields(leadgen_id):
    resp = requests.get(
        f"https://graph.facebook.com/{META_GRAPH_VERSION}/{leadgen_id}",
        params={"access_token": META_PAGE_ACCESS_TOKEN},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _map_fields(field_data):
    name = phone = email = ""
    extra = []
    for f in field_data or []:
        key = (f.get("name") or "").lower()
        values = f.get("values") or []
        value = values[0] if values else ""
        if key in NAME_KEYS and not name:
            name = value
        elif key in PHONE_KEYS:
            phone = value
        elif key in EMAIL_KEYS:
            email = value
        else:
            extra.append(f"{f.get('name')}: {value}")
    return name, phone, email, extra


def handle_leadgen_change(value):
    leadgen_id = value.get("leadgen_id")
    if not leadgen_id:
        return
    if find_by_channel("facebook", str(leadgen_id)):
        return  # Meta redelivers webhooks on retry; don't duplicate the lead.

    data = fetch_lead_fields(leadgen_id)
    name, phone, email, extra = _map_fields(data.get("field_data", []))

    portrait_lines = list(extra)
    if email:
        portrait_lines.insert(0, f"email: {email}")
    ad_name = value.get("ad_name") or data.get("ad_name") or ""
    form_name = value.get("form_name") or data.get("form_name") or ""
    if ad_name:
        portrait_lines.append(f"Реклама: {ad_name}")
    if form_name:
        portrait_lines.append(f"Форма: {form_name}")

    create_lead({
        "name": name,
        "phone": phone,
        "stage": "cold",
        "channel": "facebook",
        "externalId": str(leadgen_id),
        "portrait": "\n".join(portrait_lines),
        "notes": "Заявка з Facebook/Instagram Lead Ads",
    })
    notify_admin(f"🆕 Новий лід (Facebook Ads): {name or phone or leadgen_id}")


def handle_webhook_payload(payload):
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "leadgen":
                handle_leadgen_change(change.get("value", {}))
