import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"

STAGES = ["cold", "qualification", "qualified", "investor", "client"]

FIELDS = [
    "name", "phone", "stage", "source", "prev_contact", "portrait",
    "diagnosis", "offer", "proposal", "decision", "deal_info", "notes",
    "external_id", "next_action", "next_action_at",
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            stage TEXT NOT NULL DEFAULT 'cold',
            source TEXT DEFAULT 'manual',
            prev_contact TEXT DEFAULT '',
            portrait TEXT DEFAULT '',
            diagnosis TEXT DEFAULT '',
            offer TEXT DEFAULT '',
            proposal TEXT DEFAULT '',
            decision TEXT DEFAULT '',
            deal_info TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            external_id TEXT DEFAULT '',
            next_action TEXT DEFAULT '',
            next_action_at TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_leads_external_id ON leads(external_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            text TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def list_leads():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM leads ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_lead(lead_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_by_external_id(source, external_id):
    if not external_id:
        return None
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM leads WHERE source = ? AND external_id = ?",
        (source, external_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_lead(data):
    conn = get_conn()
    now = _now()
    values = {f: data.get(f, "") for f in FIELDS}
    values["stage"] = values["stage"] or "cold"
    cur = conn.execute(
        f"""INSERT INTO leads ({', '.join(FIELDS)}, created_at, updated_at)
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
        f"UPDATE leads SET {set_clause}, updated_at = ? WHERE id = ?",
        [*values, _now(), lead_id],
    )
    conn.commit()
    conn.close()
    return get_lead(lead_id)


def delete_lead(lead_id):
    conn = get_conn()
    conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()


def leads_with_tasks_due(on_or_before):
    """Leads whose next_action_at is set and <= on_or_before (YYYY-MM-DD)."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM leads
           WHERE next_action_at != '' AND next_action_at <= ?
           ORDER BY next_action_at""",
        (on_or_before,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_scripts():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM scripts ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_script(title, text):
    conn = get_conn()
    now = _now()
    cur = conn.execute(
        "INSERT INTO scripts (title, text, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (title, text, now, now),
    )
    conn.commit()
    script_id = cur.lastrowid
    conn.close()
    return {"id": script_id, "title": title, "text": text, "created_at": now, "updated_at": now}


def update_script(script_id, title, text):
    conn = get_conn()
    conn.execute(
        "UPDATE scripts SET title = ?, text = ?, updated_at = ? WHERE id = ?",
        (title, text, _now(), script_id),
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
