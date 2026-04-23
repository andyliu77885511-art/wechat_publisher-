"""
style_cache.py — 公众号定位风格 Prompt 缓存模块
使用 SQLite 存储非财经定位的 AI 生成风格指令，避免每次重新生成
"""
import sqlite3
import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)


class StylePromptCache:
    """
    SQLite 缓存：key=定位名称，value=AI 生成的风格 prompt 文本
    财经定位不走缓存，由 config.FINANCE_STYLE_PROMPT 硬编码提供
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表（幂等）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS style_prompt_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        position_name TEXT NOT NULL UNIQUE,
                        prompt_text TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        use_count INTEGER DEFAULT 0
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_position_name
                    ON style_prompt_cache(position_name)
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"[style_cache] 初始化数据库失败: {e}")

    def get_prompt(self, position_name: str) -> Optional[str]:
        """
        获取缓存的风格 prompt，命中时更新使用次数和时间
        返回 None 表示缓存未命中
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT prompt_text FROM style_prompt_cache WHERE position_name = ?",
                    (position_name,)
                ).fetchone()

                if row:
                    # 更新使用记录
                    conn.execute("""
                        UPDATE style_prompt_cache
                        SET last_used_at = CURRENT_TIMESTAMP,
                            use_count = use_count + 1
                        WHERE position_name = ?
                    """, (position_name,))
                    conn.commit()
                    logger.info(f"[style_cache] 缓存命中: {position_name}")
                    return row[0]

                logger.info(f"[style_cache] 缓存未命中: {position_name}")
                return None
        except Exception as e:
            logger.error(f"[style_cache] 读取缓存失败: {e}")
            return None

    def set_prompt(self, position_name: str, prompt_text: str):
        """插入或更新定位的风格 prompt"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO style_prompt_cache (position_name, prompt_text)
                    VALUES (?, ?)
                    ON CONFLICT(position_name) DO UPDATE SET
                        prompt_text = excluded.prompt_text,
                        last_used_at = CURRENT_TIMESTAMP
                """, (position_name, prompt_text))
                conn.commit()
            logger.info(f"[style_cache] 已缓存: {position_name}")
        except Exception as e:
            logger.error(f"[style_cache] 写入缓存失败: {e}")

    def clear_cache(self, position_name: Optional[str] = None):
        """清除缓存（全部或指定定位）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if position_name:
                    conn.execute(
                        "DELETE FROM style_prompt_cache WHERE position_name = ?",
                        (position_name,)
                    )
                else:
                    conn.execute("DELETE FROM style_prompt_cache")
                conn.commit()
            logger.info(f"[style_cache] 已清除缓存: {position_name or '全部'}")
        except Exception as e:
            logger.error(f"[style_cache] 清除缓存失败: {e}")
