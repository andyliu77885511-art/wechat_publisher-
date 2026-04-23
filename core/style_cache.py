"""
style_cache.py — 公众号定位风格 Prompt 缓存模块
使用 SQLite 存储非财经定位的 AI 生成风格指令，避免每次重新生成

策略：
  1. 首次 _init_db() 时调用 seed_preset_prompts()，把 config.PRESET_STYLE_PROMPTS
     里精心设计的4个定位 prompt 写入 SQLite（INSERT OR IGNORE，不覆盖用户已缓存的版本）
  2. get_prompt() 查缓存命中直接返回，财经定位不走此模块
  3. set_prompt() 供 generator.py 在动态生成后写入（降级场景）
"""
import sqlite3
import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)


class StylePromptCache:
    """
    SQLite 缓存：key=定位名称，value=风格 prompt 文本
    财经定位不走缓存，由 config.FINANCE_STYLE_PROMPT 硬编码提供
    其他4个定位（科技/生活方式/教育/职场）在初始化时从 config.PRESET_STYLE_PROMPTS 预埋
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表（幂等），并预埋各定位 preset prompt"""
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
            # 预埋 preset prompt（INSERT OR IGNORE：已存在则不覆盖）
            self._seed_preset_prompts()
        except Exception as e:
            logger.error(f"[style_cache] 初始化数据库失败: {e}")

    def _seed_preset_prompts(self):
        """
        将 config.PRESET_STYLE_PROMPTS 里的预置 prompt 写入 SQLite。
        使用 INSERT OR IGNORE，保证幂等：已有记录不会被覆盖。
        这样用户手动调用 set_prompt() 更新后也不会被下次启动重置。
        """
        preset = getattr(config, "PRESET_STYLE_PROMPTS", {})
        if not preset:
            return

        seeded = []
        skipped = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                for position_name, prompt_text in preset.items():
                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO style_prompt_cache
                            (position_name, prompt_text)
                        VALUES (?, ?)
                        """,
                        (position_name, prompt_text),
                    )
                    if cursor.rowcount > 0:
                        seeded.append(position_name)
                    else:
                        skipped.append(position_name)
                conn.commit()

            if seeded:
                logger.info(f"[style_cache] 预埋 preset prompt: {seeded}")
            if skipped:
                logger.debug(f"[style_cache] 已存在，跳过预埋: {skipped}")
        except Exception as e:
            logger.error(f"[style_cache] 预埋 preset prompt 失败: {e}")

    def get_prompt(self, position_name: str) -> Optional[str]:
        """
        获取缓存的风格 prompt，命中时更新使用次数和时间。
        返回 None 表示缓存未命中（触发 generator.py 走 API 动态生成并回写）。
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
        """插入或更新定位的风格 prompt（动态生成后回写，或手动强制更新）"""
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

    def refresh_preset(self, position_name: Optional[str] = None):
        """
        强制用 config.PRESET_STYLE_PROMPTS 重新覆盖指定定位（或全部）的缓存。
        用于 prompt 升级后手动触发刷新。
        """
        preset = getattr(config, "PRESET_STYLE_PROMPTS", {})
        targets = (
            {position_name: preset[position_name]}
            if position_name and position_name in preset
            else preset
        )
        for name, text in targets.items():
            self.set_prompt(name, text)
        logger.info(f"[style_cache] 已强制刷新 preset: {list(targets.keys())}")

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

    def get_cache_stats(self) -> list:
        """返回所有缓存条目的统计信息（供调试用）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT position_name, use_count, created_at, last_used_at,
                           length(prompt_text) as prompt_len
                    FROM style_prompt_cache
                    ORDER BY use_count DESC
                """).fetchall()
            return [
                {
                    "position": r[0],
                    "use_count": r[1],
                    "created_at": r[2],
                    "last_used_at": r[3],
                    "prompt_chars": r[4],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"[style_cache] 获取统计失败: {e}")
            return []
