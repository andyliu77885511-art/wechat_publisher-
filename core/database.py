"""
database.py — SQLite 数据库操作层
"""
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import config

DB_PATH = config.DB_PATH


def get_conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，建表、索引、触发器"""
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS materials (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT '',
            file_path   TEXT NOT NULL DEFAULT '',
            file_type   TEXT NOT NULL DEFAULT '',
            file_size   INTEGER DEFAULT 0,
            duration    INTEGER DEFAULT 0,
            status      TEXT NOT NULL DEFAULT 'pending',
            transcript  TEXT DEFAULT '',
            error_msg   TEXT DEFAULT '',
            created_at  DATETIME DEFAULT (datetime('now', 'localtime')),
            updated_at  DATETIME DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS articles (
            id              TEXT PRIMARY KEY,
            material_id     TEXT NOT NULL,
            title           TEXT NOT NULL DEFAULT '',
            content         TEXT NOT NULL DEFAULT '',
            cover_image     TEXT DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'draft',
            wx_article_id   TEXT DEFAULT '',
            wx_media_id     TEXT DEFAULT '',
            published_at    DATETIME DEFAULT NULL,
            created_at      DATETIME DEFAULT (datetime('now', 'localtime')),
            updated_at      DATETIME DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (material_id) REFERENCES materials(id)
        );

        CREATE TRIGGER IF NOT EXISTS trg_materials_updated_at
        AFTER UPDATE ON materials
        BEGIN
            UPDATE materials SET updated_at = datetime('now', 'localtime')
            WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_articles_updated_at
        AFTER UPDATE ON articles
        BEGIN
            UPDATE articles SET updated_at = datetime('now', 'localtime')
            WHERE id = NEW.id;
        END;

        CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status);
        CREATE INDEX IF NOT EXISTS idx_articles_material_id ON articles(material_id);
        CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
    """)
    conn.commit()
    conn.close()


def create_material(file_path: str, file_type: str, title: str = "") -> str:
    mid = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO materials (id, title, file_path, file_type, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (mid, title, file_path, file_type, "pending", now, now)
    )
    conn.commit()
    conn.close()
    return mid


def update_material(mid: str, **kwargs):
    kwargs["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [mid]
    conn = get_conn()
    conn.execute(f"UPDATE materials SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


from typing import Optional, List

def get_material(mid: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM materials WHERE id=?", (mid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_article(material_id: str, title: str, content: str) -> str:
    aid = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO articles (id, material_id, title, content, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (aid, material_id, title, content, "draft", now, now)
    )
    conn.commit()
    conn.close()
    return aid


def update_article(aid: str, **kwargs):
    kwargs["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [aid]
    conn = get_conn()
    conn.execute(f"UPDATE articles SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def get_article(aid: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_articles(limit: int = 20) -> List[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT a.*, m.file_type FROM articles a LEFT JOIN materials m ON a.material_id=m.id ORDER BY a.created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
