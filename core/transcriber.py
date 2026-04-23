"""
Whisper 转录模块
使用 Groq Whisper API，针对财经场景做提示词优化
"""
import os
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from typing import Optional
_client: Optional[Groq] = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            # 兼容 Streamlit Secrets
            try:
                import streamlit as st
                api_key = st.secrets.get("GROQ_API_KEY", "")
            except Exception:
                pass
        if not api_key:
            raise EnvironmentError("未设置 GROQ_API_KEY，请在 Streamlit Secrets 中配置")
        _client = Groq(api_key=api_key)
    return _client


# 财经领域专有词汇提示，提升 Whisper 识别准确率
FINANCE_PROMPT = (
    "以下是一段财经直播或短视频的录音，内容涉及A股市场、基金、宏观经济分析。"
    "专业术语包括：北向资金、南向资金、LPR、CPI、PPI、ETF、沪深300、创业板、"
    "科创板、MSCI、ROE、PE、PB、公募基金、私募基金、量化交易、做多、做空、"
    "涨停、跌停、集合竞价、连续竞价、大盘、小盘、蓝筹、白马股、成长股、价值股。"
    "请准确转录，保留数字和百分比的原始表达。"
)

# 转录内容最少有效字数（低于此值视为无效内容）
MIN_TRANSCRIPT_LENGTH = 10


def transcribe(audio_path: Path) -> str:
    """
    调用 Groq Whisper API 转录音频，返回文字稿。
    Groq 单次限制 25MB。
    如果转录结果为空或内容过少，抛出 ValueError 提示用户。
    """
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    if file_size_mb >= 25:
        raise ValueError(
            f"音频文件 {file_size_mb:.1f}MB 超过 Whisper API 单次限制（25MB）。"
            "建议先用 ffmpeg 裁剪精华片段，或联系技术支持开启分片转录。"
        )

    client = _get_client()

    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language="zh",
            prompt=FINANCE_PROMPT,
            response_format="text",
        )

    # 检查转录结果是否有效
    transcript = response.strip() if response else ""
    if len(transcript) < MIN_TRANSCRIPT_LENGTH:
        raise ValueError(
            "未能从视频/音频中识别到有效语音内容。"
            "请确认文件中包含清晰的人声，纯音乐或无声视频暂不支持处理。"
        )

    return transcript
