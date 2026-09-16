import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# DATA_DIR — де фізично лежить crm.db. За замовчуванням поруч із кодом
# (crm/), що на Railway БЕЗ підключеного Volume живе на тимчасовому
# диску: файл стирається й перестворюється заново при кожному деплої
# чи перезапуску сервера — будь-які ліди, створені між ними, губляться
# назавжди. Підключіть Railway Volume (Settings -> Volumes), змонтуйте
# його, наприклад, на /data, і задайте змінну середовища DATA_DIR=/data
# — тоді crm.db переживе будь-який наступний деплой.
DATA_DIR = Path(os.environ.get("DATA_DIR", str(Path(__file__).parent)))
DB_PATH = DATA_DIR / "crm.db"

STAGES = ["cold", "qualification", "qualified", "investor", "client", "inactive"]

# camelCase throughout, on purpose: these are the exact keys the dashboard's
# JS (ported from the Liika artifact) already reads and writes, so the API
# needs no translation layer between frontend and SQLite.
FIELDS = [
    "name", "phone", "stage", "channel", "leadSource", "assignee",
    "prevContact", "portrait", "diagnosis", "offer", "proposal", "decision",
    "dealInfo", "dealDate", "commission", "notes", "externalId",
    "nextAction", "nextActionAt", "nextActionTime", "sortOrder",
    "autoSendText", "tgUsername",
    # Кваліфікація (6 питань) + лічильник спроб виходу на контакт
    "investGoal", "location", "readyToWait", "experience", "budget", "dealTerm",
    "contactAttempts", "lastContactAttemptAt",
    # М'яке видалення — "Видалити" не стирає рядок, а ставить дату сюди,
    # і list_leads() ховає такі ліди. Дані лишаються в базі й лишаються
    # відновлюваними, поки хтось не вичистить таблицю вручну.
    "deletedAt",
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_def(field):
    if field in ("sortOrder", "contactAttempts"):
        return f"{field} INTEGER DEFAULT 0"
    return f"{field} TEXT DEFAULT ''"


def init_db():
    conn = get_conn()
    columns = ",\n            ".join(_column_def(f) for f in FIELDS)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {columns},
            createdAt TEXT NOT NULL,
            updatedAt TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_channel_external ON leads(channel, externalId)")
    # Міграція для баз, створених до додавання "autoSendText"/"tgUsername"/
    # полів кваліфікації та лічильника спроб контакту.
    for col in (
        "autoSendText", "tgUsername", "investGoal", "location", "readyToWait",
        "experience", "budget", "dealTerm", "contactAttempts", "lastContactAttemptAt",
        "deletedAt",
    ):
        try:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {_column_def(col)}")
        except sqlite3.OperationalError:
            pass  # колонка вже є
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            text TEXT NOT NULL DEFAULT '',
            stage TEXT NOT NULL DEFAULT '',
            createdAt TEXT NOT NULL,
            updatedAt TEXT NOT NULL
        )
        """
    )
    # Міграція для баз, створених до додавання "stage" (ALTER TABLE, бо
    # CREATE TABLE IF NOT EXISTS не чіпає вже існуючу таблицю).
    try:
        conn.execute("ALTER TABLE scripts ADD COLUMN stage TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # колонка вже є
    conn.commit()
    conn.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def list_leads():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM leads WHERE deletedAt = '' ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_lead(lead_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_by_channel(channel, external_id):
    if not external_id:
        return None
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM leads WHERE channel = ? AND externalId = ?",
        (channel, external_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_lead(data):
    conn = get_conn()
    now = _now()
    values = {f: data.get(f, 0 if f in ("sortOrder", "contactAttempts") else "") for f in FIELDS}
    values["stage"] = values["stage"] or "cold"
    cur = conn.execute(
        f"""INSERT INTO leads ({', '.join(FIELDS)}, createdAt, updatedAt)
            VALUES ({', '.join('?' for _ in FIELDS)}, ?, ?)""",
        [*values.values(), now, now],
    )
    conn.commit()
    lead_id = cur.lastrowid
    conn.close()
    return get_lead(lead_id)


def update_lead(lead_id, data):
    conn = get_conn()
    fields = [f for f in FIELDS if f in data]
    if not fields:
        conn.close()
        return get_lead(lead_id)
    set_clause = ", ".join(f"{f} = ?" for f in fields)
    values = [data[f] for f in fields]
    conn.execute(
        f"UPDATE leads SET {set_clause}, updatedAt = ? WHERE id = ?",
        [*values, _now(), lead_id],
    )
    conn.commit()
    conn.close()
    return get_lead(lead_id)


def delete_lead(lead_id, reason=""):
    """М'яко видаляє ліда: рядок лишається в базі з проставленим
    deletedAt, list_leads() його більше не показує. Причина (якщо
    задана) дописується в нотатки — щоб було видно, чому видалено,
    навіть після відновлення."""
    conn = get_conn()
    now = _now()
    if reason:
        row = conn.execute("SELECT notes FROM leads WHERE id = ?", (lead_id,)).fetchone()
        notes = (row["notes"] if row else "") or ""
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        notes = (notes + f"\n[{stamp}] Видалено. Причина: {reason}").strip()
        conn.execute(
            "UPDATE leads SET deletedAt = ?, notes = ?, updatedAt = ? WHERE id = ?",
            (now, notes, now, lead_id),
        )
    else:
        conn.execute(
            "UPDATE leads SET deletedAt = ?, updatedAt = ? WHERE id = ?",
            (now, now, lead_id),
        )
    conn.commit()
    conn.close()


def restore_lead(lead_id):
    conn = get_conn()
    conn.execute(
        "UPDATE leads SET deletedAt = '', updatedAt = ? WHERE id = ?",
        (_now(), lead_id),
    )
    conn.commit()
    conn.close()
    return get_lead(lead_id)


def leads_with_tasks_due(on_or_before):
    """Leads whose nextActionAt is set and <= on_or_before (YYYY-MM-DD)."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM leads
           WHERE nextActionAt != '' AND nextActionAt <= ?
           ORDER BY nextActionAt""",
        (on_or_before,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_scripts():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM scripts ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_script(title, text, stage=""):
    conn = get_conn()
    now = _now()
    cur = conn.execute(
        "INSERT INTO scripts (title, text, stage, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?)",
        (title, text, stage, now, now),
    )
    conn.commit()
    script_id = cur.lastrowid
    conn.close()
    return {"id": script_id, "title": title, "text": text, "stage": stage, "createdAt": now, "updatedAt": now}


def update_script(script_id, title, text, stage=""):
    conn = get_conn()
    conn.execute(
        "UPDATE scripts SET title = ?, text = ?, stage = ?, updatedAt = ? WHERE id = ?",
        (title, text, stage, _now(), script_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_script(script_id):
    conn = get_conn()
    conn.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
    conn.commit()
    conn.close()
