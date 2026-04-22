"""
generator.py — DeepSeek 文章生成模块
输入：转录文本 transcript
输出：{"title": str, "content": str}
"""
import time
import logging
from openai import OpenAI, APIError, APITimeoutError, RateLimitError

import config

logger = logging.getLogger(__name__)

from typing import Optional
_client: Optional[OpenAI] = None
_MAX_RETRIES = 3
_RETRY_DELAY = 2  # 首次重试等待秒数，指数退避


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not config.DEEPSEEK_API_KEY:
            raise EnvironmentError("未设置 DEEPSEEK_API_KEY，请在 .env 文件中配置")
        _client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
    return _client


def _parse_article(raw: str) -> dict:
    """
    从模型原始输出中拆分标题和正文。
    约定：第一行非空行为标题，其余为正文。
    """
    lines = raw.strip().splitlines()
    title = ""
    content_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not title and stripped:
            # 去掉可能的 Markdown 标题符号
            title = stripped.lstrip("#").strip()
        elif title:
            content_lines.append(line)

    content = "\n".join(content_lines).strip()
    return {"title": title, "content": content}


def generate_article(transcript: str) -> dict:
    """
    调用 DeepSeek API 将转录文本生成财经公众号文章。

    Args:
        transcript: 音频转录文本

    Returns:
        {"title": str, "content": str}

    Raises:
        RuntimeError: 重试耗尽仍失败时抛出
    """
    if not transcript or not transcript.strip():
        raise ValueError("转录文本为空，无法生成文章")

    user_prompt = (
        f"请将以下音视频转录稿整理为一篇财经公众号文章：\n\n{transcript}"
    )

    client = _get_client()
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info(f"[generator] 第 {attempt} 次调用 DeepSeek API ...")
            response = client.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": config.FINANCE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=4096,
            )
            raw = response.choices[0].message.content
            result = _parse_article(raw)

            if not result["title"]:
                raise ValueError("模型输出缺少标题，内容异常")
            if len(result["content"]) < 100:
                raise ValueError(f"模型输出正文过短（{len(result['content'])}字），内容异常")

            logger.info(f"[generator] 文章生成成功，标题：{result['title']}")
            return result

        except (APITimeoutError, RateLimitError) as e:
            last_error = e
            wait = _RETRY_DELAY * (2 ** (attempt - 1))
            logger.warning(f"[generator] API 限流/超时，{wait}s 后重试（{attempt}/{_MAX_RETRIES}）: {e}")
            time.sleep(wait)

        except APIError as e:
            last_error = e
            logger.warning(f"[generator] API 错误，{_RETRY_DELAY}s 后重试（{attempt}/{_MAX_RETRIES}）: {e}")
            time.sleep(_RETRY_DELAY)

        except ValueError as e:
            # 输出解析问题，直接重试
            last_error = e
            logger.warning(f"[generator] 输出解析失败，重试（{attempt}/{_MAX_RETRIES}）: {e}")

    raise RuntimeError(
        f"DeepSeek API 调用失败，已重试 {_MAX_RETRIES} 次。最后错误：{last_error}"
    )
