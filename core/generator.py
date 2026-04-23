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


def _word_count(text: str) -> int:
    """中文字数统计（去除换行和空格）"""
    if not text:
        return 0
    return len(text.replace("\n", "").replace(" ", ""))


def _strip_wx_footer(content: str) -> str:
    """
    移除文末的风险提示和空行，为后续补充段落腾出空间。
    如果没有风险提示则原样返回。
    """
    footer_marker = "以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
    idx = content.rfind(footer_marker)
    if idx >= 0:
        return content[:idx].rstrip()
    # 也尝试去掉末尾空行
    return content.rstrip()


def _append_footnote(content: str) -> str:
    """在正文末尾（换行前）追加风险提示"""
    footer = "\n\n以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
    return content.rstrip() + footer


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


def _supplement_content(content: str, title: str, transcript: str, client: OpenAI) -> str:
    """
    当字数不足时，调用 DeepSeek 补充段落。
    移除旧的风险提示后追加新段落，再加回风险提示。
    """
    current_count = _word_count(content)
    deficit = config.ARTICLE_MIN_WORDS - current_count

    logger.info(f"[generator] 字数不足，需要补充约 {deficit} 字")

    # 移除旧风险提示，避免累加
    clean_content = _strip_wx_footer(content)

    supplement_prompt = f"""当前文章标题：「{title}」
当前正文：
{clean_content}

请根据上述正文和原始转录稿，补充约 {deficit} 字的内容，使文章正文达到 {config.ARTICLE_MIN_WORDS} 字以上。

补充要求：
1. 只补充实质性内容，如：背景分析、数据解读、观点深化、案例说明
2. 不要重复已有的观点和句子
3. 保持与原文一致的语气和风格
4. 补充内容直接追加到正文中，不要加小标题

直接输出补充内容，不要加标题，不要加风险提示。"""

    try:
        response = client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": config.FINANCE_SYSTEM_PROMPT},
                {"role": "user", "content": supplement_prompt},
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        supplement = response.choices[0].message.content.strip()
        new_content = clean_content + "\n\n" + supplement
        new_content = _append_footnote(new_content)

        final_count = _word_count(new_content)
        logger.info(f"[generator] 补充后字数：{final_count}（目标 ≥{config.ARTICLE_MIN_WORDS}）")
        return new_content

    except Exception as e:
        logger.warning(f"[generator] 补充段落失败：{e}，返回原内容")
        return _append_footnote(clean_content)


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

            # 字数检测与自动补足
            word_cnt = _word_count(result["content"])
            logger.info(f"[generator] 生成字数：{word_cnt}，目标：{config.ARTICLE_MIN_WORDS}-{config.ARTICLE_MAX_WORDS}")

            if word_cnt < config.ARTICLE_MIN_WORDS:
                # 自动补充段落，最多补一次
                result["content"] = _supplement_content(
                    result["content"], result["title"], transcript, client
                )

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
