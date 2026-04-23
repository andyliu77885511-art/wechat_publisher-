"""
generator.py — DeepSeek 文章生成模块
支持财经定位（单阶段硬编码 prompt）和其他定位（两阶段调用+缓存）
输入：transcript, category, style
输出：{"title": str, "content": str}
"""
import time
import logging
from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from typing import Optional

import config
from core.style_cache import StylePromptCache

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None
_MAX_RETRIES = 3
_RETRY_DELAY = 2  # 首次重试等待秒数，指数退避

# 全局缓存实例（懒加载）
_style_cache: Optional[StylePromptCache] = None


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


def _get_style_cache() -> StylePromptCache:
    global _style_cache
    if _style_cache is None:
        _style_cache = StylePromptCache()
    return _style_cache


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
    return content.rstrip()


def _append_footnote(content: str, category: str = "财经") -> str:
    """在正文末尾追加风险提示或免责声明"""
    if category == "财经":
        footer = "\n\n以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
    else:
        footer = "\n\n以上内容仅供参考，不构成专业建议。"
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


def _call_deepseek(system_prompt: str, user_prompt: str,
                   max_tokens: int = 4096, timeout: Optional[int] = None) -> str:
    """
    基础 DeepSeek API 调用，带重试逻辑
    返回模型输出文本
    """
    client = _get_client()
    last_error = None

    kwargs = {
        "model": config.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }
    if timeout:
        kwargs["timeout"] = timeout

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except (APITimeoutError, RateLimitError) as e:
            last_error = e
            wait = _RETRY_DELAY * (2 ** (attempt - 1))
            logger.warning(f"[generator] API 限流/超时，{wait}s 后重试（{attempt}/{_MAX_RETRIES}）: {e}")
            time.sleep(wait)
        except APIError as e:
            last_error = e
            logger.warning(f"[generator] API 错误，{_RETRY_DELAY}s 后重试（{attempt}/{_MAX_RETRIES}）: {e}")
            time.sleep(_RETRY_DELAY)
        except Exception as e:
            last_error = e
            logger.warning(f"[generator] 调用异常（{attempt}/{_MAX_RETRIES}）: {e}")
            time.sleep(_RETRY_DELAY)

    raise RuntimeError(f"DeepSeek API 调用失败，已重试 {_MAX_RETRIES} 次。最后错误：{last_error}")


def _generate_position_style_prompt(position_name: str) -> str:
    """
    第一阶段：为指定定位生成风格 prompt
    超时控制：15 秒
    先查缓存，未命中再调用 API 并写入缓存
    """
    cache = _get_style_cache()

    # 查缓存
    cached = cache.get_prompt(position_name)
    if cached:
        logger.info(f"[generator] 缓存命中，跳过第一阶段: {position_name}")
        return cached

    # 调用 DeepSeek 生成风格指令
    logger.info(f"[generator] 第一阶段：生成 {position_name} 定位风格指令...")
    system_prompt = "你是公众号写作风格专家，擅长提炼各领域顶级内容的写作特征并生成可执行的写作指令。"
    user_prompt = config.META_PROMPT_STAGE1.format(position_name=position_name)

    try:
        result = _call_deepseek(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=1500,
            timeout=config.STAGE1_TIMEOUT,
        )
        # 写入缓存
        cache.set_prompt(position_name, result)
        logger.info(f"[generator] 第一阶段完成，已缓存: {position_name}")
        return result
    except Exception as e:
        logger.error(f"[generator] 第一阶段失败，降级使用通用 prompt: {e}")
        # 降级：返回通用风格指令
        return f"""你是{position_name}领域的顶级公众号作者，请参考该领域最优秀内容的写作特征，将以下内容改写为一篇高质量的公众号文章。

要求：
- 标题：口语化，有情绪感，12-20字
- 正文：结构清晰，观点鲜明，不少于1200字
- 小标题加粗，段落间空行
- 不使用 Markdown 列表符号"""


def _supplement_content(
    content: str, title: str, transcript: str, category: str, style: str
) -> str:
    """
    当字数不足时，调用 DeepSeek 补充段落。
    移除旧风险提示后追加新段落，再加回风险提示。
    """
    current_count = _word_count(content)
    deficit = config.ARTICLE_MIN_WORDS - current_count
    logger.info(f"[generator] 字数不足，需要补充约 {deficit} 字")

    clean_content = _strip_wx_footer(content)
    style_instruction = config.STYLE_INSTRUCTIONS.get(style, "")
    system_prompt = config.get_system_prompt(category, style)

    supplement_prompt = f"""当前文章标题：「{title}」
当前正文：
{clean_content}

请根据上述正文和原始内容，补充约 {deficit} 字的内容，使文章正文达到 {config.ARTICLE_MIN_WORDS} 字以上。

补充要求：
1. 只补充实质性内容，如：背景分析、数据解读、观点深化、案例说明
2. 不要重复已有的观点和句子
3. 保持与原文一致的语气和风格（{style_instruction}）
4. 补充内容直接追加到正文中，不要加小标题

直接输出补充内容，不要加标题，不要加风险提示。"""

    try:
        supplement = _call_deepseek(
            system_prompt=system_prompt,
            user_prompt=supplement_prompt,
            max_tokens=2048,
        )
        new_content = clean_content + "\n\n" + supplement.strip()
        new_content = _append_footnote(new_content, category)

        final_count = _word_count(new_content)
        logger.info(f"[generator] 补充后字数：{final_count}（目标 ≥{config.ARTICLE_MIN_WORDS}）")
        return new_content
    except Exception as e:
        logger.warning(f"[generator] 补充段落失败：{e}，返回原内容")
        return _append_footnote(clean_content, category)


def generate_article(transcript: str, category: str = "财经", style: str = "深度分析") -> dict:
    """
    调用 DeepSeek API 将转录文本生成公众号文章。

    财经定位：单阶段，直接使用硬编码 FINANCE_STYLE_PROMPT
    其他定位：两阶段调用
        第一阶段：查缓存/生成领域风格 prompt（超时 15s）
        第二阶段：组合 prompt 生成最终文章（超时 60s）

    Args:
        transcript: 音频转录文本或文档解析文本
        category: 公众号定位（财经/科技/生活方式/教育/职场）
        style: 写作风格（严肃专业/轻松幽默/深度分析/故事叙述）

    Returns:
        {"title": str, "content": str}

    Raises:
        RuntimeError: 重试耗尽仍失败时抛出
    """
    if not transcript or not transcript.strip():
        raise ValueError("转录文本为空，无法生成文章")

    logger.info(f"[generator] 定位：{category}，风格：{style}")

    # ── 确定 system prompt ──────────────────────────────────────────────────────
    if category == "财经":
        # 财经：直接使用硬编码精心设计 prompt，叠加写作风格
        style_instruction = config.STYLE_INSTRUCTIONS.get(style, "")
        system_prompt = config.FINANCE_STYLE_PROMPT
        if style != "深度分析":  # 深度分析是财经默认风格，不额外叠加
            system_prompt = system_prompt + f"\n\n## 本次写作风格要求\n{style_instruction}"
        logger.info(f"[generator] 财经定位，使用硬编码 prompt")
    else:
        # 其他定位：两阶段调用
        # 第一阶段：获取领域风格 prompt（含缓存）
        position_style_prompt = _generate_position_style_prompt(category)
        # 组合领域风格 + 写作风格
        system_prompt = config.build_stage2_system_prompt(position_style_prompt, style)
        logger.info(f"[generator] {category} 定位，两阶段调用，第二阶段生成文章")

    # ── 第二阶段：生成文章 ────────────────────────────────────────────────────────
    user_prompt = config.build_user_prompt(transcript, category)

    raw = _call_deepseek(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=4096,
        timeout=config.STAGE2_TIMEOUT,
    )

    result = _parse_article(raw)

    if not result["title"]:
        raise ValueError("模型输出缺少标题，内容异常")
    if len(result["content"]) < 100:
        raise ValueError(f"模型输出正文过短（{len(result['content'])}字），内容异常")

    logger.info(f"[generator] 文章生成成功，标题：{result['title']}")

    # ── 字数检测与自动补足 ─────────────────────────────────────────────────────────
    word_cnt = _word_count(result["content"])
    logger.info(f"[generator] 生成字数：{word_cnt}，目标：{config.ARTICLE_MIN_WORDS}-{config.ARTICLE_MAX_WORDS}")

    if word_cnt < config.ARTICLE_MIN_WORDS:
        result["content"] = _supplement_content(
            result["content"], result["title"], transcript, category, style
        )

    return result
