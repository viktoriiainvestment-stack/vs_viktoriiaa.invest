import os
import threading
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import db
import telegram_bot
import viber_bot
from notifications import notify_admin

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
DIGEST_HOUR = int(os.environ.get("DIGEST_HOUR", "9"))
ENABLE_DAILY_DIGEST = os.environ.get("ENABLE_DAILY_DIGEST", "false").lower() == "true"

app = Flask(__name__)
db.init_db()


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not ADMIN_TOKEN:
            return jsonify({"error": "ADMIN_TOKEN не налаштовано на сервері"}), 500
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else ""
        if token != ADMIN_TOKEN:
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


# ---- dashboard ----

@app.route("/")
def dashboard():
    return send_from_directory(Path(__file__).parent, "dashboard.html")


# ---- leads API ----

@app.route("/api/leads", methods=["GET"])
@require_admin
def api_list_leads():
    return jsonify(db.list_leads())


@app.route("/api/leads", methods=["POST"])
@require_admin
def api_create_lead():
    lead = db.create_lead(request.get_json(force=True) or {})
    return jsonify(lead), 201


@app.route("/api/leads/<int:lead_id>", methods=["PATCH"])
@require_admin
def api_update_lead(lead_id):
    lead = db.update_lead(lead_id, request.get_json(force=True) or {})
    if not lead:
        return jsonify({"error": "not found"}), 404
    return jsonify(lead)


@app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
@require_admin
def api_delete_lead(lead_id):
    db.delete_lead(lead_id)
    return "", 204


@app.route("/api/leads/<int:lead_id>/send", methods=["POST"])
@require_admin
def api_send_to_lead(lead_id):
    lead = db.get_lead(lead_id)
    if not lead:
        return jsonify({"error": "not found"}), 404
    text = (request.get_json(force=True) or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    if not lead.get("external_id"):
        return jsonify({"error": "У цього ліда немає каналу (Telegram/Viber) для надсилання"}), 400

    if lead["source"] == "telegram":
        telegram_bot.send_message(lead["external_id"], text)
    elif lead["source"] == "viber":
        viber_bot.send_message(lead["external_id"], text)
    else:
        return jsonify({"error": f"Невідоме джерело: {lead['source']}"}), 400

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    notes = (lead.get("notes") or "") + f"\n[{stamp}] Надіслано: {text}"
    updated = db.update_lead(lead_id, {"notes": notes.strip()})
    return jsonify(updated)


# ---- scripts (canned messages) API ----

@app.route("/api/scripts", methods=["GET"])
@require_admin
def api_list_scripts():
    return jsonify(db.list_scripts())


@app.route("/api/scripts", methods=["POST"])
@require_admin
def api_create_script():
    body = request.get_json(force=True) or {}
    script = db.create_script(body.get("title", "").strip(), body.get("text", "").strip())
    return jsonify(script), 201


@app.route("/api/scripts/<int:script_id>", methods=["PATCH"])
@require_admin
def api_update_script(script_id):
    body = request.get_json(force=True) or {}
    script = db.update_script(script_id, body.get("title", "").strip(), body.get("text", "").strip())
    if not script:
        return jsonify({"error": "not found"}), 404
    return jsonify(script)


@app.route("/api/scripts/<int:script_id>", methods=["DELETE"])
@require_admin
def api_delete_script(script_id):
    db.delete_script(script_id)
    return "", 204


# ---- Viber webhook (public, verified by Viber's own signature via the token round-trip) ----

@app.route("/viber/webhook", methods=["POST"])
def viber_webhook():
    payload = request.get_json(force=True, silent=True) or {}
    reply = viber_bot.handle_event(payload)
    return jsonify(reply or {})


# ---- background workers ----

def _digest_loop():
    last_sent_date = None
    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if now.hour == DIGEST_HOUR and last_sent_date != today:
            due = db.leads_with_tasks_due(today)
            if due:
                lines = [f"— {l['name'] or l['phone']}: {l['next_action']} ({l['next_action_at']})" for l in due]
                notify_admin("📋 Завдання на сьогодні:\n" + "\n".join(lines))
            last_sent_date = today
        time.sleep(60)


def _start_background_workers():
    if telegram_bot.bot:
        threading.Thread(target=telegram_bot.start_polling, daemon=True).start()
    if ENABLE_DAILY_DIGEST:
        threading.Thread(target=_digest_loop, daemon=True).start()


_start_background_workers()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
