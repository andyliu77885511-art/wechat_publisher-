"""
init_db.py — SQLite 数据库初始化脚本
执行方式：python init_db.py
"""

import sqlite3
import os
import sys

# 允许从项目根目录直接执行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH, UPLOAD_DIR, OUTPUT_DIR


DDL_MATERIALS = """
CREATE TABLE IF NOT EXISTS materials (
    id          TEXT PRIMARY KEY,           -- UUID
    title       TEXT NOT NULL DEFAULT '',   -- 文件名/标题
    file_path   TEXT NOT NULL,              -- 本地存储路径
    file_type   TEXT NOT NULL,              -- mp3/mp4/m4a/wav
    file_size   INTEGER DEFAULT 0,          -- 字节数
    duration    INTEGER DEFAULT 0,          -- 时长（秒），-1 表示未知
    status      TEXT NOT NULL DEFAULT 'pending',
                                            -- pending/transcribing/transcribed/generating/completed/failed
    transcript  TEXT DEFAULT '',            -- Whisper 输出的完整转录文本
    error_msg   TEXT DEFAULT '',            -- 失败时的错误信息
    created_at  DATETIME DEFAULT (datetime('now', 'localtime')),
    updated_at  DATETIME DEFAULT (datetime('now', 'localtime'))
);
"""

DDL_ARTICLES = """
CREATE TABLE IF NOT EXISTS articles (
    id              TEXT PRIMARY KEY,       -- UUID
    material_id     TEXT NOT NULL,          -- 关联素材 ID
    title           TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',   -- 正文（纯文本，段落间空行分隔）
    cover_image     TEXT DEFAULT '',        -- 封面图本地路径
    status          TEXT NOT NULL DEFAULT 'draft',
                                            -- draft/published/failed
    wx_article_id   TEXT DEFAULT '',        -- 微信返回的 article_id
    wx_media_id     TEXT DEFAULT '',        -- 微信返回的 media_id（草稿）
    published_at    DATETIME DEFAULT NULL,
    created_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    updated_at      DATETIME DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (material_id) REFERENCES materials(id)
);
"""

DDL_TRIGGER_MATERIALS = """
CREATE TRIGGER IF NOT EXISTS trg_materials_updated_at
AFTER UPDATE ON materials
BEGIN
    UPDATE materials SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;
"""

DDL_TRIGGER_ARTICLES = """
CREATE TRIGGER IF NOT EXISTS trg_articles_updated_at
AFTER UPDATE ON articles
BEGIN
    UPDATE articles SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;
"""

INDEX_MATERIALS_STATUS = """
CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status);
"""

INDEX_ARTICLES_MATERIAL = """
CREATE INDEX IF NOT EXISTS idx_articles_material_id ON articles(material_id);
"""

INDEX_ARTICLES_STATUS = """
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
"""


def init_db(db_path: str = DB_PATH) -> None:
    """初始化数据库，创建表结构和索引"""
    # 确保存储目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.executescript("\n".join([
            DDL_MATERIALS,
            DDL_ARTICLES,
            DDL_TRIGGER_MATERIALS,
            DDL_TRIGGER_ARTICLES,
            INDEX_MATERIALS_STATUS,
            INDEX_ARTICLES_MATERIAL,
            INDEX_ARTICLES_STATUS,
        ]))
        conn.commit()
        print(f"[OK] 数据库初始化完成: {db_path}")
        print(f"[OK] 上传目录: {UPLOAD_DIR}")
        print(f"[OK] 输出目录: {OUTPUT_DIR}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
