import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "investor.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            name TEXT NOT NULL,
            drive_folder_id TEXT DEFAULT '',
            drive_folder_link TEXT DEFAULT '',
            last_report TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_projects_chat ON projects(chat_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_state (
            chat_id TEXT PRIMARY KEY,
            active_project_id INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            source_url TEXT DEFAULT '',
            drive_file_id TEXT DEFAULT '',
            drive_file_link TEXT DEFAULT '',
            added_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_materials_project ON materials(project_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            location TEXT DEFAULT '',
            text TEXT NOT NULL,
            FOREIGN KEY(material_id) REFERENCES materials(id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id)"
    )
    conn.commit()
    conn.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


# ---- projects ----

def list_projects(chat_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM projects WHERE chat_id = ? ORDER BY id", (str(chat_id),)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_project_by_name(chat_id, name):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM projects WHERE chat_id = ? AND name = ? COLLATE NOCASE",
        (str(chat_id), name),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_project(project_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_project(chat_id, name, drive_folder_id="", drive_folder_link=""):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO projects (chat_id, name, drive_folder_id, drive_folder_link, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(chat_id), name, drive_folder_id, drive_folder_link, _now()),
    )
    conn.commit()
    project_id = cur.lastrowid
    conn.close()
    return get_project(project_id)


def save_report(project_id, report_text):
    conn = get_conn()
    conn.execute("UPDATE projects SET last_report = ? WHERE id = ?", (report_text, project_id))
    conn.commit()
    conn.close()


def set_active_project(chat_id, project_id):
    conn = get_conn()
    conn.execute(
        """INSERT INTO chat_state (chat_id, active_project_id) VALUES (?, ?)
           ON CONFLICT(chat_id) DO UPDATE SET active_project_id = excluded.active_project_id""",
        (str(chat_id), project_id),
    )
    conn.commit()
    conn.close()


def get_active_project(chat_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT active_project_id FROM chat_state WHERE chat_id = ?", (str(chat_id),)
    ).fetchone()
    conn.close()
    if not row or not row["active_project_id"]:
        return None
    return get_project(row["active_project_id"])


# ---- materials & chunks ----

def add_material(project_id, kind, title, source_url="", drive_file_id="", drive_file_link=""):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO materials (project_id, kind, title, source_url, drive_file_id, drive_file_link, added_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (project_id, kind, title, source_url, drive_file_id, drive_file_link, _now()),
    )
    conn.commit()
    material_id = cur.lastrowid
    conn.close()
    return get_material(material_id)


def get_material(material_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_materials(project_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM materials WHERE project_id = ? ORDER BY id", (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_chunks(material_id, project_id, chunks):
    """chunks: list of (location, text) tuples."""
    if not chunks:
        return
    conn = get_conn()
    conn.executemany(
        "INSERT INTO chunks (material_id, project_id, location, text) VALUES (?, ?, ?, ?)",
        [(material_id, project_id, location, text) for location, text in chunks],
    )
    conn.commit()
    conn.close()


def list_chunks(project_id):
    conn = get_conn()
    rows = conn.execute(
        """SELECT chunks.*, materials.title AS material_title, materials.drive_file_link AS drive_file_link,
                  materials.kind AS material_kind
           FROM chunks JOIN materials ON materials.id = chunks.material_id
           WHERE chunks.project_id = ? ORDER BY chunks.id""",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_chunks_for_chat(chat_id):
    """Фрагменти з УСІХ проектів цього чату — для питань "по всій базі"
    (порівняння проектів, вибір найкращого, оцінка ризику по регіону)."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT chunks.*, materials.title AS material_title, materials.drive_file_link AS drive_file_link,
                  materials.kind AS material_kind, projects.name AS project_name
           FROM chunks
           JOIN materials ON materials.id = chunks.material_id
           JOIN projects ON projects.id = chunks.project_id
           WHERE projects.chat_id = ? ORDER BY chunks.id""",
        (str(chat_id),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
