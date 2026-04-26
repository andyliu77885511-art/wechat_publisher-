"""
app.py — 公众号自动发布工具 Streamlit 主入口
流程：上传文件 -> 转录/生成 -> 预览编辑 -> 发布确认
"""
import streamlit as st
from pathlib import Path
import time
import logging

import config
from core.file_handler import (
    save_uploaded_file,
    get_audio_path,
    get_duration_seconds,
    estimate_transcribe_minutes,
    extract_text_from_doc,
)
from core.transcriber import transcribe
from core.generator import generate_article
from core.database import (
    init_db,
    create_material,
    update_material,
    create_article,
    update_article,
    list_articles,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout="centered",
)

# ── openclaw.ai 风格 CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0a1628 0%, #1a2332 50%, #0d1b2a 100%) !important;
    min-height: 100vh;
}
.main .block-container {
    max-width: 820px;
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}
