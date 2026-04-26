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

# ── 自定义样式（全面美化版）───────────────────────────────────────────────────────
st.markdown("""
<style>
/* ===== OpenClaw 风格设计系统 ===== */
/* 参考: openclaw.ai — 深空黑 + Coral红 + 玻璃卡片 + 极简极客调性 */

/* ===== 字体引入 ===== */
@import url('https://api.fontshare.com/v2/css?f[]=clash-display@700,600,500&f[]=satoshi@400,500,700&display=swap');

/* ===== CSS 变量 ===== */
:root {
    --coral-bright: #FF4D4D;
    --coral-dim: rgba(255, 77, 77, 0.7);
    --coral-glow: rgba(255, 77, 77, 0.25);
    --bg-primary: #12122a;
    --bg-secondary: #1a1a2e;
    --bg-card: rgba(255, 255, 255, 0.08);
    --bg-card-hover: rgba(255, 255, 255, 0.12);
    --border-subtle: rgba(255, 255, 255, 0.15);
    --border-card: rgba(255, 255, 255, 0.18);
    --text-primary: #f0f0f0;
    --text-secondary: rgba(255, 255, 255, 0.72);
    --text-muted: rgba(255, 255, 255, 0.50);
    --accent: #FF4D4D;
    --accent-cyan: #00e5cc;
    --success: #34d399;
    --warning: #fbbf24;
    --error: #f87171;
}

/* ===== 动画 Keyframes ===== */
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-20px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes slideInUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes coralPulse {
    0%   { box-shadow: 0 0 0 0 var(--coral-glow); }
    70%  { box-shadow: 0 0 0 10px rgba(255,77,77,0); }
    100% { box-shadow: 0 0 0 0 rgba(255,77,77,0); }
}
@keyframes clawFloat {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-4px); }
}
@keyframes borderGlow {
    0%   { border-color: rgba(255,77,77,0.4); }
    50%  { border-color: rgba(255,77,77,0.8); box-shadow: 0 0 20px rgba(255,77,77,0.2); }
    100% { border-color: rgba(255,77,77,0.4); }
}

/* ===== 全局背景 ===== */
.stApp {
    background:
        radial-gradient(ellipse at 75% 10%, rgba(0,229,204,0.20) 0%, transparent 45%),
        radial-gradient(ellipse at 10% 80%, rgba(180,0,0,0.30) 0%, transparent 45%),
        #12122a !important;
    min-height: 100vh;
    font-family: 'Satoshi', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* 背景星空纹理 */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse at 20% 50%, rgba(255,77,77,0.04) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 20%, rgba(0,229,204,0.08) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 80%, rgba(255,77,77,0.02) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

.main .block-container {
    max-width: 780px;
    padding-top: 2.5rem;
    padding-bottom: 4rem;
    position: relative;
    z-index: 1;
}

/* ===== 全局文字颜色 ===== */
.stApp, .stApp * {
    color: var(--text-primary);
}

/* ===== Header ===== */
.app-header {
    animation: fadeInDown 0.6s ease both;
    font-family: 'Clash Display', 'Satoshi', sans-serif !important;
    font-size: 2.1rem;
    font-weight: 700;
    letter-spacing: -0.8px;
    color: var(--text-primary) !important;
    -webkit-text-fill-color: unset !important;
    background: none !important;
    background-clip: unset !important;
    margin-bottom: 0.15rem;
    line-height: 1.1;
}
.app-header-accent {
    color: var(--coral-bright);
}
.app-subtitle {
    animation: fadeInDown 0.8s ease both;
    color: var(--text-muted) !important;
    font-size: 0.82rem;
    margin-top: 0;
    font-family: 'Satoshi', sans-serif;
    letter-spacing: 0.2px;
}

/* ===== 分隔线 ===== */
hr {
    border: none !important;
    height: 1px !important;
    background: var(--border-subtle) !important;
    margin: 1.5rem 0 !important;
}

/* ===== 步骤指示器（Claw 风格胶囊）===== */
.step-capsule-done {
    display: inline-block;
    background: rgba(52, 211, 153, 0.12);
    color: var(--success) !important;
    border: 1px solid rgba(52, 211, 153, 0.3);
    border-radius: 6px;
    padding: 3px 12px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.2px;
    animation: slideInUp 0.3s ease both;
}
.step-capsule-active {
    display: inline-block;
    background: rgba(255, 77, 77, 0.12);
    border: 1px solid rgba(255, 77, 77, 0.4);
    border-radius: 6px;
    padding: 3px 12px;
    font-size: 0.78rem;
    font-weight: 600;
    animation: coralPulse 1.8s infinite, slideInUp 0.3s ease both;
    /* 渐变文字 */
    background-image: linear-gradient(135deg, #FF4D4D 0%, #C8B8B8 50%, #00E5CC 100%), rgba(255,77,77,0.12);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}
.step-capsule-wait {
    display: inline-block;
    background: transparent;
    color: var(--text-muted) !important;
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    padding: 3px 12px;
    font-size: 0.78rem;
    font-weight: 500;
}

/* ===== 上传区卡片（OpenClaw 风格）===== */
.upload-box {
    border: 1.5px dashed rgba(255, 77, 77, 0.3);
    border-radius: 14px;
    padding: 3rem 2rem;
    text-align: center;
    background: rgba(255, 77, 77, 0.03);
    margin: 1rem 0;
    transition: all 0.25s ease;
    animation: slideInUp 0.45s ease both;
    animation-delay: 0.08s;
}
.upload-box:hover {
    border-color: rgba(255, 77, 77, 0.6);
    background: rgba(255, 77, 77, 0.06);
    animation: borderGlow 2s ease infinite;
}
.upload-icon {
    font-size: 2.8rem;
    display: block;
    margin-bottom: 0.6rem;
    filter: drop-shadow(0 0 8px rgba(255,77,77,0.5));
    animation: clawFloat 3s ease-in-out infinite;
}
.upload-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text-primary) !important;
    margin-bottom: 0.3rem;
    font-family: 'Clash Display', 'Satoshi', sans-serif;
}
.upload-title-accent {
    color: var(--coral-bright);
}
.upload-hint {
    color: var(--text-muted);
    font-size: 0.82rem;
    line-height: 1.5;
}

/* ===== 子步骤状态 ===== */
.step-done  { color: var(--success) !important; font-weight: 600; }
.step-active { color: var(--coral-bright) !important; font-weight: 600; }
.step-wait  { color: var(--text-muted) !important; }

/* ===== 提示框（玻璃卡片风格）===== */
.warn-box {
    background: rgba(251, 191, 36, 0.06);
    border: 1px solid rgba(251, 191, 36, 0.25);
    border-radius: 10px;
    padding: 0.9rem 1.3rem;
    margin: 1rem 0;
    color: var(--warning) !important;
    font-size: 0.88rem;
    animation: slideInUp 0.35s ease both;
}
.success-box {
    background: rgba(52, 211, 153, 0.06);
    border: 1px solid rgba(52, 211, 153, 0.25);
    border-radius: 10px;
    padding: 0.9rem 1.3rem;
    margin: 1rem 0;
    color: var(--success) !important;
    font-size: 0.88rem;
    animation: slideInUp 0.35s ease both;
}
.error-box {
    background: rgba(248, 113, 113, 0.06);
    border: 1px solid rgba(248, 113, 113, 0.25);
    border-radius: 10px;
    padding: 0.9rem 1.3rem;
    margin: 1rem 0;
    color: var(--error) !important;
    font-size: 0.88rem;
    animation: slideInUp 0.35s ease both;
}

/* ===== 文章编辑区（左 Coral 条）===== */
.editor-card {
    border-left: 3px solid var(--coral-bright);
    border-radius: 0 10px 10px 0;
    padding: 1.2rem 1.4rem;
    background: var(--bg-card);
    margin-bottom: 1rem;
    animation: slideInUp 0.45s ease both;
}

/* ===== 输入框 ===== */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-family: 'Satoshi', sans-serif !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--coral-bright) !important;
    box-shadow: 0 0 0 2px var(--coral-glow) !important;
    outline: none !important;
    background: rgba(255,255,255,0.055) !important;
}

/* ===== 按钮（Coral 主色）===== */
.stButton > button {
    background: linear-gradient(135deg, #cc0000 0%, #ff4d4d 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 1.4rem !important;
    font-family: 'Satoshi', sans-serif !important;
    letter-spacing: 0.1px;
    box-shadow: 0 2px 12px rgba(255,77,77,0.3) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    background: #ff3333 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(255,77,77,0.45) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 6px rgba(255,77,77,0.25) !important;
}
/* 次要按钮 */
.stButton > button[kind="secondary"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-card) !important;
    box-shadow: none !important;
    color: var(--text-secondary) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: var(--bg-card-hover) !important;
    border-color: rgba(255,77,77,0.3) !important;
    box-shadow: none !important;
    transform: translateY(-1px) !important;
}

/* ===== 下载按钮 ===== */
.stDownloadButton > button {
    background: rgba(52, 211, 153, 0.1) !important;
    color: var(--success) !important;
    border: 1px solid rgba(52, 211, 153, 0.35) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Satoshi', sans-serif !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
}
.stDownloadButton > button:hover {
    background: rgba(52, 211, 153, 0.18) !important;
    border-color: rgba(52, 211, 153, 0.6) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(52,211,153,0.2) !important;
}

/* ===== 标签/Caption ===== */
.stCaption, .stApp label {
    color: var(--text-secondary) !important;
    font-size: 0.82rem !important;
}
.stMarkdown p {
    color: var(--text-primary) !important;
    line-height: 1.65;
}

/* ===== 进度条 ===== */
.stProgress > div > div > div {
    background: var(--coral-bright) !important;
    border-radius: 999px !important;
}
.stProgress > div > div {
    background: rgba(255,255,255,0.06) !important;
    border-radius: 999px !important;
}

/* ===== Expander（折叠区）===== */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    transition: background 0.2s;
}
.streamlit-expanderHeader:hover {
    background: var(--bg-card-hover) !important;
}

/* ===== file uploader ===== */
div[data-testid="stFileUploader"] > div { border: none !important; }
div[data-testid="stFileUploader"] section {
    background: rgba(255,77,77,0.04) !important;
    border: 1.5px dashed rgba(255,77,77,0.25) !important;
    border-radius: 10px !important;
    transition: border-color 0.2s, background 0.2s;
}
div[data-testid="stFileUploader"] section:hover {
    border-color: rgba(255,77,77,0.5) !important;
    background: rgba(255,77,77,0.07) !important;
}

/* ===== 标题（h2/h3）===== */
h1, h2, h3 {
    font-family: 'Clash Display', 'Satoshi', sans-serif !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #FF4D4D 0%, #C8B8B8 50%, #00E5CC 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    letter-spacing: -0.3px;
}

/* claw-accent 前缀标记 */
.claw-accent {
    color: var(--coral-bright);
    margin-right: 0.35rem;
    font-weight: 600;
}

/* ===== Section 标题行样式 ===== */
.section-title-row {
    display: flex;
    align-items: center;
    margin-bottom: 1.2rem;
    gap: 0.4rem;
}
.section-title-main {
    font-family: 'Clash Display', 'Satoshi', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.2px;
}

/* ===== 公众号定位选择器容器 ===== */
.selector-container {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    transition: border-color 0.2s;
}
.selector-container:hover {
    border-color: rgba(255,77,77,0.2);
}
.selector-label {
    color: var(--text-secondary);
    font-size: 0.85rem;
    font-weight: 500;
    white-space: nowrap;
}
.selector-label-accent {
    color: var(--coral-bright);
}

/* ===== Selectbox ===== */
div[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}

/* ===== Radio 按钮 ===== */
.stRadio > div > label {
    color: var(--text-secondary) !important;
    transition: color 0.15s;
}
.stRadio > div > label:hover {
    color: var(--text-primary) !important;
}
[data-testid="stRadio"] label[data-testid="stMarkdownContainer"] {
    color: var(--text-primary) !important;
}

/* ===== Info/Warning/Success 原生提示 ===== */
div[data-testid="stAlert"] {
    border-radius: 10px !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
}

/* ===== Divider ===== */
[data-testid="stDivider"] {
    border-color: var(--border-subtle) !important;
}

/* ===== Sidebar（如果有）===== */
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

/* ===== 滚动条美化 ===== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(255,77,77,0.25);
    border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(255,77,77,0.45); }

/* ===== 选中文字颜色 ===== */
::selection {
    background: rgba(255,77,77,0.25);
    color: #fff;
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

# ── 公众号定位选择器（常驻顶部，随时可切换）────────────────────────────────────────
with st.container():
    col_pos_label, col_pos_sel = st.columns([1, 3])
    with col_pos_label:
        st.markdown(
            '<div style="padding-top:8px;color:rgba(255,255,255,0.7);font-size:0.9rem;">📌 公众号定位</div>',
            unsafe_allow_html=True,
        )
    with col_pos_sel:
        # 如果当前 category 是自定义名称（不在列表里），选择器显示"其他"
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
        if selected_category == "其他":
            # 自定义定位输入框
            _custom_val = "" if _current_in_list else st.session_state.category
            custom_category = st.text_input(
                "输入自定义定位名称",
                value=_custom_val,
                placeholder="例如：母婴、健身、旅游...",
                label_visibility="collapsed",
                key="custom_category_input",
            )
            _effective = custom_category.strip() if custom_category.strip() else "其他"
            if _effective != st.session_state.category:
                st.session_state.category = _effective
                st.rerun()
        else:
            if selected_category != st.session_state.category:
                st.session_state.category = selected_category
                st.rerun()

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
        '<div class="upload-title">拖拽文件到此处，或点击下方按钮选择文件</div>'
        '<div class="upload-hint">支持格式：音视频（mp3 / mp4 / m4a / wav / avi / mov / mkv / flv / wmv）| 文档（pdf / txt / docx / md）</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "选择文件",
        type=config.ALLOWED_FILE_TYPES,
        label_visibility="collapsed",
    )

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
            file_ready = True
            # 预计上传时间提示（按 2MB/s 估算）
            if file_size_mb > 2:
                est_upload_sec = int(file_size_mb / 2)
                if est_upload_sec < 60:
                    est_upload_str = f"约 {est_upload_sec} 秒"
                else:
                    est_upload_str = f"约 {est_upload_sec // 60} 分钟"
                st.caption(f"⏱️ 文件较大，点击「开始处理」后预计上传 {est_upload_str}，请耐心等待")

    # 写作风格配置（文章级，每次处理前选择）
    st.divider()
    st.markdown('<div style="color:rgba(255,255,255,0.7);font-size:0.9rem;margin-bottom:6px;">🎨 写作风格</div>', unsafe_allow_html=True)
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

    # 按钮始终显示，未上传时灰色不可点，上传成功后蓝色可点
    if st.button("🚀 开始处理", type="primary", use_container_width=True, disabled=not file_ready):
        # 上传进度反馈
        _file_size_mb = uploaded.size / (1024 * 1024)
        _est_sec = max(2, int(_file_size_mb / 2)) if _file_size_mb > 1 else 1
        _upload_bar = st.progress(0, text="📤 正在上传文件，请稍候...")
        _upload_status = st.empty()

        # 模拟上传进度（实际 IO 在 save_uploaded_file 中完成）
        # 先推进到 70%，给用户反馈，剩余 30% 在 save 完成后完成
        for _i in range(1, 8):
            time.sleep(max(0.15, _est_sec * 0.07))
            _pct = _i / 10
            _upload_bar.progress(_pct, text=f"📤 正在上传文件...（{int(_pct * 100)}%）")

        _upload_status.caption("💾 正在保存文件到服务器...")
        file_path, file_type = save_uploaded_file(uploaded)
        _upload_bar.progress(1.0, text="✅ 上传完成！")
        _upload_status.empty()
        time.sleep(0.3)
        _upload_bar.empty()

        material_id = create_material(file_path, file_type, title=uploaded.name)

        st.session_state.file_path = file_path
        st.session_state.file_type = file_type
        st.session_state.material_id = material_id
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
            reset_state()
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
