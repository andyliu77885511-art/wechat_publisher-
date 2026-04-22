"""
media.py — [已废弃] 音视频处理模块

注意：此模块功能已合并到 core/file_handler.py。
保留此文件仅供参考，请勿在新代码中引用。
所有文件上传和音频提取功能统一使用 core/file_handler.py。
"""

# ===== 以下代码不再使用，仅存档 =====

import subprocess
from pathlib import Path


UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_file(uploaded_file) -> Path:
    """[废弃] 请使用 core.file_handler.save_uploaded_file"""
    dest = UPLOAD_DIR / uploaded_file.name
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest


def extract_audio(video_path: Path) -> Path:
    """[废弃] 请使用 core.file_handler.extract_audio"""
    audio_path = video_path.with_suffix(".wav")
    if audio_path.exists():
        return audio_path
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 提取音频失败：{result.stderr}")
    return audio_path


def get_audio_duration(audio_path: Path) -> float:
    """[废弃] 请使用 core.file_handler.get_duration_seconds"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0
