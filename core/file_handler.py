"""
file_handler.py — 文件上传处理 + ffmpeg 音频提取
"""
import os
import subprocess
import uuid
from pathlib import Path

import config

UPLOAD_DIR = config.UPLOAD_DIR


def save_uploaded_file(uploaded_file) -> tuple[str, str]:
    """
    保存 Streamlit 上传的文件到本地
    返回 (file_path, file_type)
    """
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix.lower()
    uid = str(uuid.uuid4())
    dest = os.path.join(UPLOAD_DIR, f"{uid}{suffix}")
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest, suffix.lstrip(".")


def extract_audio(video_path: str) -> str:
    """
    用 ffmpeg 从视频文件提取音频，保存为 mp3
    返回音频文件路径
    """
    audio_path = video_path.rsplit(".", 1)[0] + "_audio.mp3"
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-ar", "16000",
        "-ac", "1",
        "-ab", "64k",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 提取音频失败：{result.stderr[-500:]}")
    return audio_path


def get_audio_path(file_path: str, file_type: str) -> str:
    """
    如果是视频文件则提取音频，如果已是音频直接返回
    """
    video_types = {"mp4", "avi", "mov", "mkv", "flv", "wmv"}
    if file_type in video_types:
        return extract_audio(file_path)
    return file_path


def get_duration_seconds(audio_path: str) -> int:
    """
    获取音频时长（秒）
    """
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return int(float(result.stdout.strip()))
    except Exception:
        return 0


def estimate_transcribe_minutes(duration_seconds: int) -> str:
    """
    根据音频时长估算转录耗时
    """
    mins = duration_seconds / 60
    if mins <= 10:
        return "约1分钟"
    elif mins <= 30:
        return "约2-4分钟"
    elif mins <= 60:
        return "约4-8分钟"
    else:
        return f"约{int(mins / 8)}-{int(mins / 6)}分钟"
