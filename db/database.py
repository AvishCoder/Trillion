import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trillion.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT DEFAULT 'New Chat',
            provider TEXT DEFAULT 'openrouter',
            model TEXT DEFAULT 'openrouter/free',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
    """)
    conn.commit()
    conn.close()


def create_conversation(provider="openrouter", model="openrouter/free"):
    conn = get_conn()
    cid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO conversations (id, provider, model) VALUES (?, ?, ?)",
        (cid, provider, model),
    )
    conn.commit()
    conn.close()
    return cid


def get_conversations():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_conversation(cid):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM conversations WHERE id = ?", (cid,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_conversation_title(cid, title):
    conn = get_conn()
    conn.execute(
        "UPDATE conversations SET title = ?, updated_at = datetime('now') WHERE id = ?",
        (title, cid),
    )
    conn.commit()
    conn.close()


def delete_conversation(cid):
    conn = get_conn()
    conn.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
    conn.execute("DELETE FROM conversations WHERE id = ?", (cid,))
    conn.commit()
    conn.close()


def save_message(conversation_id, role, content):
    conn = get_conn()
    mid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
        (mid, conversation_id, role, content),
    )
    conn.execute(
        "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
        (conversation_id,),
    )
    conn.commit()
    conn.close()
    return mid


def get_messages(conversation_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
