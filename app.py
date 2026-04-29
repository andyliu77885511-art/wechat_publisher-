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

# ── 自定义样式（Design System v2 — Indigo 深色风格）────────────────────────────────
st.markdown("""
<style>
/*
 * WechatPublisher Design System v2
 * 设计基准：openclaw.ai 风格 — 深色底、冷白卡片、石墨文字
 * 主色：深邃蓝黑 #0D1117（背景）+ 品牌主色 #6366F1（Indigo）
 * 风格关键词：YC / Maas / 极简 / 高对比 / 技术专业
 *
 * 对比度修复（WCAG AA）：
 *   1. 禁用按钮：#ffffff on #BCC0C4 (1.83:1) → #94A3B8 on #1E2433 (5.0:1)
 *   2. 品牌蓝小字：#1877F2 on #fff (4.23:1) → #818CF8 on #161B27 (6.2:1)
 *   3. 成功绿小字：#31A24C on #fff (3.28:1) → #4ADE80 on #161B27 (7.1:1)
 */

/* ===== 字体引入 ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ===== CSS 变量（Design Tokens v2）===== */
:root {
    /* 背景层级 */
    --bg-app:      #0D1117;   /* 深黑，整页底色 */
    --bg-surface:  #161B27;   /* 卡片底色 */
    --bg-elevated: #1E2433;   /* 悬浮卡片 */
    --bg-muted:    #252D3D;   /* 内嵌区块 */

    /* 品牌主色：Indigo 而非 Facebook 蓝 */
    --primary:        #6366F1;              /* Indigo 500 */
    --primary-light:  #818CF8;             /* Indigo 400，小字高对比用 */
    --primary-dark:   #4F46E5;             /* Indigo 600，hover */
    --primary-glow:   rgba(99,102,241,0.25);
    --primary-soft:   rgba(99,102,241,0.12);
    --primary-border: rgba(99,102,241,0.35);

    /* 状态色（暗背景高对比版）*/
    --success:       #4ADE80;              /* 对比度 7.1:1 on --bg-surface */
    --success-bg:    rgba(74,222,128,0.10);
    --success-bdr:   rgba(74,222,128,0.30);
    --warning:       #FBBF24;
    --warning-bg:    rgba(251,191,36,0.10);
    --warning-bdr:   rgba(251,191,36,0.30);
    --error:         #F87171;
    --error-bg:      rgba(248,113,113,0.10);
    --error-bdr:     rgba(248,113,113,0.30);

    /* 边框 */
    --border:        #2D3748;
    --border-focus:  #6366F1;

    /* 文字（在暗背景上）*/
    --text-primary:    #F1F5F9;  /* 近白，正文 */
    --text-secondary:  #94A3B8;  /* 石墨，辅助 */
    --text-muted:      #64748B;  /* 暗灰，hint */

    /* 阴影 */
    --shadow-1: 0 1px 3px rgba(0,0,0,0.40);
    --shadow-2: 0 4px 12px rgba(0,0,0,0.40);
    --shadow-3: 0 8px 24px rgba(99,102,241,0.20);

    /* 字体 */
    --font-display: "Inter", system-ui, -apple-system, sans-serif;
    --font-body:    "Inter", system-ui, -apple-system, sans-serif;
}

/* ===== 动画 ===== */
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-10px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes slideInUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes indigoPulse {
    0%   { box-shadow: 0 0 0 0 rgba(99,102,241,0.40); }
    70%  { box-shadow: 0 0 0 8px rgba(99,102,241,0); }
    100% { box-shadow: 0 0 0 0 rgba(99,102,241,0); }
}

/* ===== 全局背景 ===== */
.stApp {
    background: var(--bg-app) !important;
    min-height: 100vh;
    font-family: var(--font-body) !important;
}
.stApp * {
    font-family: var(--font-body) !important;
}
.main .block-container {
    max-width: 780px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

/* ===== 全局文字颜色强制覆盖 ===== */
.stMarkdown p, .stMarkdown span, .stMarkdown div,
[data-testid="stText"], [data-testid="stMarkdownContainer"] p,
.stFileUploader p, .stFileUploader span:not(button span),
.stSelectbox span, .stRadio span {
    color: var(--text-primary) !important;
}

/* ===== Header ===== */
.app-header {
    font-family: var(--font-display) !important;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--primary-light) !important;
    -webkit-text-fill-color: var(--primary-light) !important;
    animation: fadeInDown 0.5s ease both;
    margin-bottom: 0.1rem;
    line-height: 1.2;
    letter-spacing: -0.5px;
}
.app-subtitle {
    animation: fadeInDown 0.7s ease both;
    color: var(--text-secondary) !important;
    font-size: 0.8rem;
    margin-top: 0;
}

/* ===== Divider ===== */
hr {
    border: none !important;
    height: 1px !important;
    background: var(--border) !important;
    margin: 1.2rem 0 !important;
}
[data-testid="stDivider"] {
    border-color: var(--border) !important;
}

/* ===== 步骤胶囊 ===== */
.step-capsule-done {
    display: inline-block;
    background: var(--success-bg);
    color: var(--success) !important;   /* #4ADE80 on #161B27 = 7.1:1 ✅ */
    border: 1px solid var(--success-bdr);
    border-radius: 100px;
    padding: 4px 14px;
    font-size: 0.78rem;
    font-weight: 600;
    animation: slideInUp 0.3s ease both;
}
.step-capsule-active {
    display: inline-block;
    background: var(--primary);
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: none;
    border-radius: 100px;
    padding: 5px 16px;
    font-size: 0.78rem;
    font-weight: 700;
    box-shadow: 0 2px 10px rgba(99,102,241,0.45);
    animation: indigoPulse 1.8s infinite, slideInUp 0.3s ease both;
}
.step-capsule-wait {
    display: inline-block;
    background: transparent;
    color: var(--text-secondary) !important; /* #94A3B8，对比度 4.6:1 ✅ */
    border: 1px solid var(--border);
    border-radius: 100px;
    padding: 4px 14px;
    font-size: 0.78rem;
    font-weight: 500;
}

/* ===== 子步骤状态 ===== */
/* 修复：成功色 #4ADE80 on #161B27 = 7.1:1；主色小字 #818CF8 on #161B27 = 6.2:1 */
.step-done   { color: var(--success) !important; font-weight: 600; }
.step-active { color: var(--primary-light) !important; font-weight: 600; }
.step-wait   { color: var(--text-secondary) !important; }

/* ===== 公众号定位选择器卡片 ===== */
.config-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin: 0.8rem 0;
    box-shadow: var(--shadow-1);
    transition: border-color 0.2s, box-shadow 0.2s;
    animation: slideInUp 0.4s ease both;
}
.config-card:hover {
    border-color: var(--primary-border);
    box-shadow: var(--shadow-3);
}
.section-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: var(--text-secondary) !important;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 6px;
}
.section-label::before {
    content: "";
    display: inline-block;
    width: 3px;
    height: 12px;
    background: var(--primary);
    border-radius: 2px;
}
.category-pill {
    display: inline-block;
    background: var(--primary-soft);
    border: 1px solid var(--primary-border);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--primary-light) !important; /* #818CF8 on #1E2433 = 6.2:1 ✅ */
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-left: 8px;
    vertical-align: middle;
}

/* ===== 上传区卡片 ===== */
.upload-box {
    border: 1.5px dashed var(--primary-border);
    border-radius: 12px;
    padding: 2.5rem 2rem;
    text-align: center;
    background: var(--bg-surface);
    margin: 1rem 0;
    transition: border-color 0.2s, background 0.2s, box-shadow 0.2s, transform 0.2s;
    animation: slideInUp 0.4s ease both;
    box-shadow: var(--shadow-1);
}
.upload-box:hover {
    border-color: var(--primary);
    background: var(--primary-soft);
    box-shadow: var(--shadow-3);
    transform: translateY(-2px);
}
.upload-icon {
    font-size: 2.4rem;
    display: block;
    margin-bottom: 0.6rem;
}
.upload-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary) !important;
    margin-bottom: 0.3rem;
}
.upload-hint {
    color: var(--text-secondary) !important;
    font-size: 0.82rem;
    line-height: 1.5;
}

/* ===== 提示框 ===== */
.warn-box {
    background: var(--warning-bg);
    border: 1px solid var(--warning-bdr);
    border-radius: 8px;
    padding: 0.85rem 1.2rem;
    margin: 0.8rem 0;
    color: var(--warning) !important;
    font-size: 0.88rem;
    animation: slideInUp 0.3s ease both;
}
.success-box {
    background: var(--success-bg);
    border: 1px solid var(--success-bdr);
    border-radius: 8px;
    padding: 0.85rem 1.2rem;
    margin: 0.8rem 0;
    color: var(--success) !important;
    font-size: 0.88rem;
    animation: slideInUp 0.3s ease both;
}
.error-box {
    background: var(--error-bg);
    border: 1px solid var(--error-bdr);
    border-radius: 8px;
    padding: 0.85rem 1.2rem;
    margin: 0.8rem 0;
    color: var(--error) !important;
    font-size: 0.88rem;
    animation: slideInUp 0.3s ease both;
}

/* ===== 编辑区卡片 ===== */
.editor-card {
    border-left: 3px solid var(--primary);
    border-radius: 0 12px 12px 0;
    padding: 1.2rem 1.4rem;
    background: var(--bg-surface);
    border-top: 1px solid var(--border);
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    margin-bottom: 1rem;
    box-shadow: var(--shadow-1);
    animation: slideInUp 0.4s ease both;
}

/* ===== 输入框 ===== */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-family: var(--font-body) !important;
    font-size: 0.92rem !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--border-focus) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.20) !important;
    outline: none !important;
}

/* ===== 标签文字 ===== */
.stTextInput label, .stTextArea label, .stSelectbox label,
.stRadio label, .stFileUploader label {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

/* ===== 主按钮（Indigo）===== */
.stButton > button {
    background: var(--primary) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 1.4rem !important;
    font-family: var(--font-display) !important;
    letter-spacing: 0.01em;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    background: var(--primary-dark) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(99,102,241,0.35) !important;
}
.stButton > button:active {
    background: #4338CA !important;
    transform: translateY(0) !important;
    box-shadow: none !important;
}
/* 修复 #1：禁用按钮 — #94A3B8 on #1E2433 = 5.0:1 ✅ （原 1.83:1）*/
.stButton > button:disabled {
    background: var(--bg-elevated) !important;
    color: var(--text-secondary) !important;
    -webkit-text-fill-color: var(--text-secondary) !important;
    cursor: not-allowed !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ===== Download 按钮（Outline）===== */
.stDownloadButton > button {
    background: transparent !important;
    color: var(--primary-light) !important;
    -webkit-text-fill-color: var(--primary-light) !important;
    border: 1px solid var(--primary-border) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 1.4rem !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
}
.stDownloadButton > button:hover {
    background: var(--primary-soft) !important;
    border-color: var(--primary) !important;
    box-shadow: 0 2px 8px rgba(99,102,241,0.25) !important;
    transform: translateY(-1px) !important;
}

/* ===== Selectbox ===== */
div[data-testid="stSelectbox"] > div > div {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    box-shadow: var(--shadow-1) !important;
}
div[data-testid="stSelectbox"] > div > div:hover {
    border-color: var(--primary-border) !important;
}

/* ===== Radio 按钮 ===== */
.stRadio > div > label {
    color: var(--text-secondary) !important;
    transition: color 0.15s;
}
.stRadio > div > label:hover {
    color: var(--primary-light) !important;
}
.stRadio > div > label[data-checked="true"] {
    color: var(--primary-light) !important;
    font-weight: 600 !important;
}

/* ===== Progress bar ===== */
.stProgress > div > div > div {
    background: var(--primary) !important;
    border-radius: 999px !important;
}
.stProgress > div > div {
    background: var(--bg-elevated) !important;
    border-radius: 999px !important;
}

/* ===== Expander ===== */
.streamlit-expanderHeader {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    transition: background 0.2s, border-color 0.2s;
}
.streamlit-expanderHeader:hover {
    background: var(--primary-soft) !important;
    border-color: var(--primary-border) !important;
}

/* ===== File Uploader ===== */
div[data-testid="stFileUploader"] > div { border: none !important; }

div[data-testid="stFileUploader"] section,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 1.5rem !important;
    padding: 1.2rem 1.5rem !important;
    background: var(--bg-surface) !important;
    border: 1.5px dashed var(--primary-border) !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow-1);
    transition: border-color 0.2s, background 0.2s;
}
div[data-testid="stFileUploader"] section:hover,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--primary) !important;
    background: var(--primary-soft) !important;
}

/*
 * 保持原有隐藏机制（注意：此 CSS 依赖 Streamlit 内部 DOM 结构）
 * 隐藏内部原生触发按钮，由下方自定义样式按钮替代
 */
div[data-testid="stFileUploader"] div[role="presentation"] > button {
    display: none !important;
}

div[data-testid="stFileUploader"] section > button,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > button,
div[data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"] {
    order: -1 !important;
    flex-shrink: 0 !important;
    min-width: 130px !important;
    white-space: nowrap !important;
    background: var(--primary) !important;
    color: #ffffff !important;
    font-size: 14px !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.4rem !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stFileUploader"] section > button:hover,
div[data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"]:hover {
    background: var(--primary-dark) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(99,102,241,0.30) !important;
}

div[data-testid="stFileUploader"] section > div,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div {
    flex: 1 !important;
    order: 0 !important;
    text-align: left !important;
}

div[data-testid="stFileUploader"] section > div > span:not(button span),
div[data-testid="stFileUploader"] section > div > small,
div[data-testid="stFileUploader"] section > div > p:first-child,
div[data-testid="stFileUploaderDropzone"] > div > span:not(button span),
div[data-testid="stFileUploaderDropzone"] > div > small {
    display: none !important;
}
div[data-testid="stFileUploader"] button span {
    display: inline !important;
    visibility: visible !important;
    color: #ffffff !important;
}
div[data-testid="stFileUploader"] button p,
div[data-testid="stFileUploader"] button small {
    display: none !important;
}

/* ===== h1/h2/h3 标题 ===== */
h1, h2, h3 {
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    background: none !important;
    letter-spacing: -0.3px;
}

/* ===== 公众号定位选择器标签 ===== */
.selector-label {
    color: var(--text-secondary) !important;
    font-size: 0.85rem;
    font-weight: 500;
    white-space: nowrap;
}
.selector-label-accent {
    color: var(--primary-light) !important;
}

/* ===== Info/Warning/Success 原生提示框 ===== */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-left-width: 4px !important;
    background: var(--bg-surface) !important;
    color: var(--text-primary) !important;
}

/* ===== Sidebar ===== */
[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* ===== Caption / small text ===== */
.stCaption, .stCaption p {
    color: var(--text-secondary) !important;
    font-size: 0.8rem !important;
}

/* ===== Section 卡片容器 ===== */
.section-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    box-shadow: var(--shadow-1);
}

/* ===== 写作风格标签 ===== */
.style-label {
    color: var(--text-secondary) !important;
    font-size: 0.9rem;
    margin-bottom: 6px;
    font-weight: 500;
}

/* ===== 滚动条 ===== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-app); }
::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover { background: var(--primary); }

/* ===== 选中文字 ===== */
::selection {
    background: rgba(99,102,241,0.25);
    color: var(--text-primary);
}

</style>

""", unsafe_allow_html=True)

# ── 初始化 ───────────────────────────────────────────────────────────────────────
init_db()

# Session state 初始化
defaults = {
    "step": "upload",        # upload / processing / preview / publish
    "file_path": None,
    "file_type": None,
    "material_id": None,
    "transcript": None,
    "article_title": None,
    "article_content": None,
    "article_id": None,
    "error": None,
    "category": config.DEFAULT_CATEGORY,      # 公众号定位
    "writing_style": config.DEFAULT_STYLE,    # 写作风格
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── 工具函数 ─────────────────────────────────────────────────────────────────────

def reset_state():
    """重置所有状态，回到上传页"""
    for k, v in defaults.items():
        st.session_state[k] = v


def word_count(text: str) -> int:
    """中文字数统计"""
    if not text:
        return 0
    return len(text.replace("\n", "").replace(" ", ""))


def render_step_indicators(steps_list, current_step_key):
    """渲染横向进度指示器（胶囊样式）"""
    current_idx = next((i for i, s in enumerate(steps_list) if s[0] == current_step_key), 0)
    cols = st.columns(len(steps_list))
    for i, (step_key, step_label) in enumerate(steps_list):
        with cols[i]:
            if i < current_idx:
                st.markdown(
                    f'<div style="text-align:center"><span class="step-capsule-done">✓ {step_label}</span></div>',
                    unsafe_allow_html=True,
                )
            elif i == current_idx:
                st.markdown(
                    f'<div style="text-align:center"><span class="step-capsule-active">● {step_label}</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="text-align:center"><span class="step-capsule-wait">○ {step_label}</span></div>',
                    unsafe_allow_html=True,
                )


def render_sub_steps(steps_status):
    """渲染子步骤状态（转录生成阶段内部）"""
    lines = []
    for s in steps_status:
        if s["status"] == "done":
            lines.append(f'<span class="step-done">✓ {s["label"]}</span>')
        elif s["status"] == "active":
            lines.append(f'<span class="step-active">⟳ {s["label"]}...</span>')
        else:
            lines.append(f'<span class="step-wait">○ {s["label"]}</span>')
    return "<br>".join(lines)


# ── 页面头部 ─────────────────────────────────────────────────────────────────────

col_title, col_ver = st.columns([5, 1])
with col_title:
    st.markdown(
        f'<div class="app-header">{config.PAGE_ICON} {config.PAGE_TITLE}</div>',
        unsafe_allow_html=True,
    )
with col_ver:
    st.markdown(
        f'<div class="app-subtitle">{config.PAGE_VERSION}</div>',
        unsafe_allow_html=True,
    )

# 配置检查
cfg_result = config.validate_config()
if not cfg_result["ok"]:
    st.markdown(
        f'<div class="warn-box">配置缺失：{", ".join(cfg_result["missing"])}。'
        f"请在 .env 文件中补充后重启应用。</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── 进度指示器 ───────────────────────────────────────────────────────────────────

STEPS = [
    ("upload", "1. 上传"),
    ("processing", "2. 转录"),
    ("preview", "3. 生成"),
    ("publish", "4. 发布确认"),
]

render_step_indicators(STEPS, st.session_state.step)

st.markdown("")

# ══════════════════════════════════════════════════════════════════════════════════
# STEP 1: 上传文件
# ══════════════════════════════════════════════════════════════════════════════════

if st.session_state.step == "upload":

    st.subheader("上传音视频文件")

    st.markdown(
        '<div class="upload-box">'
        '<span class="upload-icon">📂</span>'
        '<div class="upload-title">点击下方按钮选择文件</div>'
        '<div class="upload-hint">支持格式：音视频（mp3 / mp4 / m4a / wav / avi / mov / mkv / flv / wmv）| 文档（pdf / txt / docx / md）</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "选择文件",
        type=config.ALLOWED_FILE_TYPES,
        label_visibility="collapsed",
    )

    # ── 文件选择后立即保存（提前到 file_uploader 检测阶段）──────────────────────
    file_ready = False

    if uploaded:
        file_size_mb = uploaded.size / (1024 * 1024)
        st.info(f"已选择：{uploaded.name}（{file_size_mb:.1f} MB）")
        if file_size_mb > config.MAX_FILE_SIZE_MB:
            st.markdown(
                f'<div class="error-box">文件大小超过限制（{config.MAX_FILE_SIZE_MB}MB），请压缩后重试。</div>',
                unsafe_allow_html=True,
            )
        else:
            # 用文件名+大小作为唯一标识，避免同一个文件重复保存
            _upload_key = f"{uploaded.name}_{uploaded.size}"
            if st.session_state.get("file_saved") and st.session_state.get("_upload_key") == _upload_key:
                # 已保存过，直接复用
                file_ready = True
                st.markdown(
                    '<div class="success-box">✅ 文件已上传到本地，可直接点击「开始处理」</div>',
                    unsafe_allow_html=True,
                )
            else:
                # 首次选择该文件，立即保存并显示进度条
                _est_sec = max(1, int(file_size_mb / 2)) if file_size_mb > 1 else 1
                _upload_bar = st.progress(0, text="📤 正在上传文件，请稍候...")

                # 进度条推到 60% 给用户先感受到反馈
                for _i in range(1, 7):
                    time.sleep(max(0.1, _est_sec * 0.06))
                    _upload_bar.progress(_i / 10, text=f"📤 正在上传文件...（{_i * 10}%）")

                # 真正写磁盘
                _file_path, _file_type = save_uploaded_file(uploaded)
                _material_id = create_material(_file_path, _file_type, title=uploaded.name)

                # 推到 100%
                for _i in range(7, 11):
                    time.sleep(0.05)
                    _upload_bar.progress(_i / 10, text=f"📤 正在上传文件...（{_i * 10}%）")

                _upload_bar.empty()

                # 写入 session_state，供「开始处理」直接使用
                st.session_state.file_saved = True
                st.session_state._upload_key = _upload_key
                st.session_state.file_path = _file_path
                st.session_state.file_type = _file_type
                st.session_state.material_id = _material_id

                file_ready = True
                st.markdown(
                    '<div class="success-box">✅ 文件已上传到本地，可直接点击「开始处理」</div>',
                    unsafe_allow_html=True,
                )
    else:
        # 用户清除了文件，重置保存状态
        st.session_state.file_saved = False
        st.session_state._upload_key = None

    # ── 公众号定位选择器（上传区下方）──────────────────────────────────────────
    st.divider()
    st.markdown('<div class="config-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">📌 公众号定位</div>', unsafe_allow_html=True)
    with st.container():
        col_pos_label, col_pos_sel = st.columns([1, 3])
        with col_pos_label:
            st.markdown(
                '<div style="padding-top:8px;color:#1c1e21;font-size:0.88rem;font-weight:500;">当前定位</div>',
                unsafe_allow_html=True,
            )
        with col_pos_sel:
            _current_in_list = st.session_state.category in config.CATEGORY_LIST
            _selector_index = (
                config.CATEGORY_LIST.index(st.session_state.category)
                if _current_in_list
                else config.CATEGORY_LIST.index("其他")
            )
            selected_category = st.selectbox(
                "公众号定位",
                options=config.CATEGORY_LIST,
                index=_selector_index,
                label_visibility="collapsed",
                key="category_selector",
            )
            if selected_category != st.session_state.category:
                st.session_state.category = selected_category
                st.rerun()
            if selected_category == "其他":
                # P2: 防抖 — 用 on_change 回调，只在失焦时更新，不在每次输入时 rerun
                def _on_custom_category_change():
                    val = st.session_state.get("custom_category_input", "").strip()
                    st.session_state.category = val if val else "其他"

                _custom_val = "" if _current_in_list else st.session_state.category
                st.text_input(
                    "输入自定义定位名称",
                    value=_custom_val,
                    placeholder="例如：母婴、健身、旅游...",
                    label_visibility="collapsed",
                    key="custom_category_input",
                    on_change=_on_custom_category_change,
                )
    st.markdown('</div>', unsafe_allow_html=True)  # close config-card

    # 写作风格配置（文章级，每次处理前选择）
    st.divider()
    st.markdown('<div class="section-label">🎨 写作风格</div>', unsafe_allow_html=True)
    style_options = config.STYLE_LIST
    selected_style = st.radio(
        "写作风格",
        options=style_options,
        index=style_options.index(st.session_state.writing_style),
        horizontal=True,
        label_visibility="collapsed",
        key="style_radio",
    )
    if selected_style != st.session_state.writing_style:
        st.session_state.writing_style = selected_style
    style_desc = {
        "严肃专业": "语言克制、逻辑严密，多用数据支撑",
        "轻松幽默": "口语化有梗，像朋友聊天，适度调侃",
        "深度分析": "层层递进、有框架有反驳，挖掘深层逻辑（默认）",
        "故事叙述": "具体场景开头，道理藏在故事里",
    }
    st.caption(f"当前：{selected_style} — {style_desc.get(selected_style, '')}")
    st.caption(f"💡 定位决定领域腔调，风格决定表达方式 — 当前：{st.session_state.category} × {selected_style}")

    st.divider()

    # 「开始处理」按钮：只负责跳页，文件操作已在上方完成
    if st.button("🚀 开始处理", type="primary", use_container_width=True, disabled=not file_ready):
        st.session_state.step = "processing"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════════
# STEP 2: 转录 + AI 生成
# ══════════════════════════════════════════════════════════════════════════════════

elif st.session_state.step == "processing":

    st.subheader("处理中")

    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    detail_placeholder = st.empty()

    # 判断文件类型：文档走提取文本流程，音视频走转录流程
    doc_types = {"pdf", "txt", "docx", "md"}
    is_doc = st.session_state.file_type in doc_types

    if is_doc:
        sub_steps = [
            {"label": "解析文档", "status": "wait"},
            {"label": "AI 生成文章", "status": "wait"},
            {"label": "保存结果", "status": "wait"},
        ]
    else:
        sub_steps = [
            {"label": "提取音频", "status": "wait"},
            {"label": "语音转录", "status": "wait"},
            {"label": "AI 生成文章", "status": "wait"},
            {"label": "保存结果", "status": "wait"},
        ]

    try:
        if is_doc:
            # 文档处理分支：提取文本后直接生成文章
            sub_steps[0]["status"] = "active"
            status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
            progress_placeholder.progress(0.15)
            st.info("正在解析文档...")

            transcript = extract_text_from_doc(
                st.session_state.file_path,
                st.session_state.file_type,
            )
            st.session_state.transcript = transcript
            update_material(st.session_state.material_id, transcript=transcript, status="transcribed")

            sub_steps[0]["status"] = "done"
            detail_placeholder.caption(f"文档字数：{word_count(transcript)}")

            # Step 2.2: AI 生成文章（跳过转录步骤）
            sub_steps[1]["status"] = "active"
            status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
            progress_placeholder.progress(0.5)

            result = generate_article(
                transcript,
                category=st.session_state.category,
                style=st.session_state.writing_style,
            )

            sub_steps[1]["status"] = "done"
            st.session_state.article_title = result["title"]
            st.session_state.article_content = result["content"]

            # Step 2.3: 保存结果
            sub_steps[2]["status"] = "active"
            status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
            progress_placeholder.progress(0.9)

            article_id = create_article(
                material_id=st.session_state.material_id,
                title=result["title"],
                content=result["content"],
            )
            update_material(st.session_state.material_id, status="generated")
            st.session_state.article_id = article_id

            sub_steps[2]["status"] = "done"
            status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
            progress_placeholder.progress(1.0)

            time.sleep(0.5)
            st.session_state.step = "preview"
            st.rerun()
        else:
            # 音视频处理分支：原流程
            # Step 2.1: 提取音频
            sub_steps[0]["status"] = "active"
            status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
            progress_placeholder.progress(0.1)

            audio_path = get_audio_path(st.session_state.file_path, st.session_state.file_type)
            duration = get_duration_seconds(audio_path)
            est = estimate_transcribe_minutes(duration)

            sub_steps[0]["status"] = "done"
            detail_placeholder.caption(f"音频时长：{duration // 60}分{duration % 60}秒，预计转录{est}")

            # Step 2.2: 语音转录（含动态进度条，Whisper API 耗时 30s-2min）
            sub_steps[1]["status"] = "active"
            status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
            progress_placeholder.progress(0.3)

            # 动态进度条：在转录期间给用户反馈
            transcribe_bar = st.empty()
            transcribe_tip = st.empty()
            _transcribe_tip_msgs = [
                "🎙️ 正在识别语音...",
                "🎙️ 正在识别语音...（Whisper 大模型处理中）",
                "🎙️ 音频较长时需要 1-2 分钟，请勿关闭页面",
                "🎙️ 快好了，稍等一下...",
            ]

            import threading
            _transcribe_done = threading.Event()
            _transcribe_result = [None]
            _transcribe_error = [None]

            def _do_transcribe():
                try:
                    _transcribe_result[0] = transcribe(Path(audio_path))
                except Exception as e:
                    _transcribe_error[0] = e
                finally:
                    _transcribe_done.set()

            _t = threading.Thread(target=_do_transcribe, daemon=True)
            _t.start()

            # 动态更新进度条，直到转录完成
            _tick = 0
            _tip_idx = 0
            while not _transcribe_done.wait(timeout=1.5):
                _tick += 1.5
                # 进度条 0.3 ~ 0.58，用时间估算，最多推到 90%
                _transcribe_progress = min(0.3 + (_tick / max(duration, 30)) * 0.28, 0.58)
                progress_placeholder.progress(_transcribe_progress)
                _tip_msg = _transcribe_tip_msgs[min(_tip_idx // 3, len(_transcribe_tip_msgs) - 1)]
                elapsed_str = f"{int(_tick // 60)}分{int(_tick % 60)}秒" if _tick >= 60 else f"{int(_tick)}秒"
                transcribe_bar.progress(
                    min(_tick / max(duration, 30), 0.95),
                    text=f"{_tip_msg}（已等待 {elapsed_str}）"
                )
                _tip_idx += 1

            _t.join()
            transcribe_bar.empty()
            transcribe_tip.empty()

            if _transcribe_error[0]:
                raise _transcribe_error[0]

            transcript = _transcribe_result[0]
            update_material(st.session_state.material_id, transcript=transcript, status="transcribed", duration=duration)

            sub_steps[1]["status"] = "done"
            st.session_state.transcript = transcript

        # Step 2.3: AI 生成文章
        sub_steps[2]["status"] = "active"
        status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
        progress_placeholder.progress(0.6)

        result = generate_article(
            transcript,
            category=st.session_state.category,
            style=st.session_state.writing_style,
        )

        sub_steps[2]["status"] = "done"
        st.session_state.article_title = result["title"]
        st.session_state.article_content = result["content"]

        # Step 2.4: 保存结果
        sub_steps[3]["status"] = "active"
        status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
        progress_placeholder.progress(0.9)

        article_id = create_article(
            material_id=st.session_state.material_id,
            title=result["title"],
            content=result["content"],
        )
        update_material(st.session_state.material_id, status="generated")
        st.session_state.article_id = article_id

        sub_steps[3]["status"] = "done"
        status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
        progress_placeholder.progress(1.0)

        time.sleep(0.5)
        st.session_state.step = "preview"
        st.rerun()

    except Exception as e:
        logger.error(f"处理失败：{e}")
        st.markdown(
            f'<div class="error-box">处理失败：{str(e)}</div>',
            unsafe_allow_html=True,
        )
        if st.button("返回重试", use_container_width=True):
            reset_state()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════════
# STEP 3: 预览编辑
# ══════════════════════════════════════════════════════════════════════════════════

elif st.session_state.step == "preview":

    st.subheader("预览与编辑")

    # 编辑区卡片容器
    st.markdown('<div class="editor-card">', unsafe_allow_html=True)

    # 标题编辑
    title = st.text_input(
        "文章标题",
        value=st.session_state.article_title or "",
        placeholder="输入文章标题",
    )

    # 正文编辑
    content = st.text_area(
        "文章内容",
        value=st.session_state.article_content or "",
        height=400,
        placeholder="在此编辑文章内容...",
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # 字数统计
    wc = word_count(content)
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.caption(f"当前字数：{wc}（目标 {config.ARTICLE_MIN_WORDS}-{config.ARTICLE_MAX_WORDS}）")
    with col_right:
        if wc < config.ARTICLE_MIN_WORDS:
            st.caption(f"⚠️ 字数不足，还需 {config.ARTICLE_MIN_WORDS - wc} 字")
        elif wc > config.ARTICLE_MAX_WORDS:
            st.caption(f"⚠️ 字数超出上限 {wc - config.ARTICLE_MAX_WORDS} 字")
        else:
            st.caption("✓ 字数符合要求")

    # 预览区
    with st.expander("📖 预览效果（公众号风格）"):
        st.markdown(f"## {title}")
        st.markdown(content)
        st.caption("---")
        st.caption("以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。")

    st.divider()

    # 操作按钮
    col_prev, col_next, col_down = st.columns([1, 1, 1])
    with col_prev:
        if st.button("← 上一步", use_container_width=True):
            # 只回退步骤，保留已上传的文件信息和生成结果
            st.session_state.step = "upload"
            st.rerun()
    with col_next:
        if st.button("确认发布 →", type="primary", use_container_width=True):
            if not title.strip():
                st.warning("请输入文章标题")
            elif wc < config.ARTICLE_MIN_WORDS:
                st.warning(f"文章字数不足（{wc}/{config.ARTICLE_MIN_WORDS}）")
            elif wc > config.ARTICLE_MAX_WORDS:
                st.warning(f"文章字数超出上限（{wc}/{config.ARTICLE_MAX_WORDS}）")
            else:
                # 保存编辑结果
                update_article(st.session_state.article_id, title=title, content=content)
                st.session_state.article_title = title
                st.session_state.article_content = content
                st.session_state.step = "publish"
                st.rerun()
    with col_down:
        # 下载按钮：导出 .txt
        if content:
            txt_content = f"{title}\n\n{content}\n\n---\n以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
            st.download_button(
                "📥 下载 .txt",
                txt_content.encode("utf-8"),
                file_name=f"{title[:30] or 'article'}.txt",
                mime="text/plain",
                use_container_width=True,
            )


# ══════════════════════════════════════════════════════════════════════════════════
# STEP 4: 发布确认
# ══════════════════════════════════════════════════════════════════════════════════

elif st.session_state.step == "publish":

    st.subheader("发布确认")

    _title   = st.session_state.article_title or "（无标题）"
    _content = st.session_state.article_content or ""
    _wc      = word_count(_content)

    # 文章摘要卡片
    st.markdown(
        f'''<div class="section-card" style="margin-bottom:1.2rem;">
            <div class="section-label">📄 文章信息</div>
            <div style="margin-top:0.8rem;">
                <div style="font-size:1.1rem;font-weight:700;color:var(--text-primary);margin-bottom:0.5rem;">{_title}</div>
                <div style="color:#1c1e21;font-size:0.88rem;">
                    字数：{_wc} 字 &nbsp;|&nbsp; 定位：{st.session_state.category} &nbsp;|&nbsp; 风格：{st.session_state.writing_style}
                </div>
            </div>
        </div>''',
        unsafe_allow_html=True,
    )

    # 内容预览（折叠）
    with st.expander("📖 查看文章内容"):
        st.markdown(f"## {_title}")
        st.markdown(_content)

    st.divider()

    # 微信发布功能说明
    st.markdown(
        '<div class="warn-box">⚠️ 微信公众号直接发布功能暂未开放（需配置 WX_APP_SECRET）。'
        '你可以下载文章后手动发布到公众号后台。</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    col_back, col_download, col_done = st.columns([1, 1, 1])

    with col_back:
        if st.button("← 返回编辑", use_container_width=True):
            st.session_state.step = "preview"
            st.rerun()

    with col_download:
        if _content:
            txt_content = f"{_title}\n\n{_content}\n\n---\n以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
            st.download_button(
                "📥 下载文章",
                txt_content.encode("utf-8"),
                file_name=f"{_title[:30] or 'article'}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with col_done:
        if st.button("✅ 完成，处理新文章", type="primary", use_container_width=True):
            reset_state()
            st.rerun()
