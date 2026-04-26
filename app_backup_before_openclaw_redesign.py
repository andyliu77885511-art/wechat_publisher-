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
# publisher 模块保留备用，暂不从主流程调用
# from core.publisher import (
#     upload_image,
#     create_draft,
#     publish_draft,
#     WechatAPIError,
# )
from core.database import (
    init_db,
    create_material,
    update_material,
    create_article,
    update_article,
    list_articles,
)

# ── 日志 ────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── 页面配置 ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout="centered",
)

# ── 自定义样式（openclaw.ai 风格改版）───────────────────────────────────────────
st.markdown("""
<style>
/* ===== 全局背景（深蓝灰渐变，专业克制）===== */
.stApp {
    background: linear-gradient(135deg, #0a1628 0%, #1a2332 50%, #0d1b2a 100%) !important;
    min-height: 100vh;
}
.main .block-container {
    max-width: 820px;
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

/* ===== Header 样式（白色简洁，无渐变）===== */
.app-header {
    color: #ffffff;
    font-size: 2.2rem;
    font-weight: 700;
    letter-spacing: -0.8px;
    margin-bottom: 0.3rem;
}
.app-subtitle {
    color: rgba(255,255,255,0.4);
    font-size: 0.88rem;
    margin-top: 0;
    font-weight: 400;
}

/* ===== 分隔线（细线，低调）===== */
hr {
    border: none !important;
    height: 1px !important;
    background: rgba(255,255,255,0.08) !important;
    margin: 1.8rem 0 !important;
}

/* ===== 公众号定位选择器卡片（重点改版区域）===== */
.position-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.5rem 1.8rem;
    margin: 1.2rem 0;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}
.position-card:hover {
    border-color: rgba(255,165,0,0.3);
    box-shadow: 0 4px 20px rgba(255,165,0,0.08);
}
.position-label {
    color: rgba(255,255,255,0.65);
    font-size: 0.92rem;
    font-weight: 500;
    margin-bottom: 0.8rem;
    display: block;
}

/* ===== 步骤指示器（简洁圆点风格）===== */
