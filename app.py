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

# ── 自定义样式（Material Design / Google 风格）──────────────────────────────────────
st.markdown("""
<style>
/* ===== 字体引入 (Google Fonts) ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto:wght@400;500;700&display=swap');

/* ===== CSS 变量 (Facebook Design tokens) ===== */
:root {
    /* 背景 — Facebook 灰，层次更深 */
    --bg-app:     #f0f2f5;
    --bg-surface: #ffffff;
    --bg-elevated:#ffffff;
    --bg-muted:   #e4e6ea;

    /* 主色 Facebook Blue */
    --primary:       #1877f2;
    --primary-dark:  #0d5bbf;
    --primary-light: #e7f0ff;
    --primary-glow:  rgba(24, 119, 242, 0.22);

    /* 状态色 */
    --success:      #31a24c;
    --success-bg:   #e4f5e9;
    --success-bdr:  #9fcea8;
    --warning:      #f0a500;
    --warning-bg:   #fff4d9;
    --warning-bdr:  #f5d073;
    --error:        #e02020;
    --error-bg:     #fde8e8;
    --error-bdr:    #f3a8a8;

    /* 边框 — 更明显 */
    --border:       #c5c8ce;
    --border-focus: #1877f2;

    /* 文字 — Facebook 深色系 */
    --text-primary:   #1c1e21;
    --text-secondary: #4b4f56;
    --text-muted:     #8a8d91;
    --text-on-blue:   #ffffff;

    /* 阴影 — 更明显的层次感 */
    --shadow-1: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.10);
    --shadow-2: 0 2px 8px rgba(0,0,0,0.14), 0 1px 4px rgba(0,0,0,0.10);
    --shadow-3: 0 6px 16px rgba(0,0,0,0.16), 0 2px 6px rgba(0,0,0,0.12);

    /* 字体 */
    --font-body:    'Inter', 'Roboto', system-ui, sans-serif;
}

/* ===== 动画 ===== */
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-12px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes slideInUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes ripple {
    0%   { transform: scale(0.95); box-shadow: 0 0 0 0 var(--primary-glow); }
    70%  { transform: scale(1);    box-shadow: 0 0 0 8px rgba(26,115,232,0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(26,115,232,0); }
}

/* ===== 全局背景 ===== */
.stApp {
    background: var(--bg-app) !important;
    min-height: 100vh;
    font-family: var(--font-body) !important;
}
.stApp * {
    color: var(--text-primary);
    font-family: var(--font-body) !important;
}

.main .block-container {
    max-width: 780px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

/* ===== 全局文字覆盖 (确保白色背景上不出现白字) ===== */
p, span, label, div, li, td, th, caption {
    color: var(--text-primary) !important;
}

/* ===== Header ===== */
.app-header {
    animation: fadeInDown 0.5s ease both;
    font-family: var(--font-body) !important;
    font-size: 1.9rem;
    font-weight: 700;
    color: var(--primary) !important;
    -webkit-text-fill-color: var(--primary) !important;
    margin-bottom: 0.1rem;
    line-height: 1.2;
    letter-spacing: -0.3px;
}
.app-subtitle {
    animation: fadeInDown 0.7s ease both;
    color: var(--text-muted) !important;
    font-size: 0.8rem;
    margin-top: 0;
    font-family: var(--font-body);
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
    color: var(--success) !important;
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
    border: 1.5px solid var(--primary-dark);
    border-radius: 100px;
    padding: 5px 16px;
    font-size: 0.78rem;
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(24,119,242,0.40);
    animation: ripple 1.8s infinite, slideInUp 0.3s ease both;
}
.step-capsule-wait {
    display: inline-block;
    background: transparent;
    color: var(--text-muted) !important;
    border: 1px solid var(--border);
    border-radius: 100px;
    padding: 4px 14px;
    font-size: 0.78rem;
    font-weight: 500;
}

/* ===== 子步骤状态 ===== */
.step-done   { color: var(--success) !important; font-weight: 600; }
.step-active { color: var(--primary) !important; font-weight: 600; }
.step-wait   { color: var(--text-muted) !important; }

/* ===== 上传区卡片 ===== */
.upload-box {
    border: 2px dashed var(--border);
    border-radius: 12px;
    padding: 2.5rem 2rem;
    text-align: center;
    background: var(--bg-surface);
    margin: 1rem 0;
    transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
    animation: slideInUp 0.4s ease both;
    box-shadow: var(--shadow-2);
}
.upload-box:hover {
    border-color: var(--primary);
    background: var(--primary-light);
    box-shadow: var(--shadow-2);
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
    color: #7b5800 !important;
    font-size: 0.88rem;
    animation: slideInUp 0.3s ease both;
}
.success-box {
    background: var(--success-bg);
    border: 1px solid var(--success-bdr);
    border-radius: 8px;
    padding: 0.85rem 1.2rem;
    margin: 0.8rem 0;
    color: #137333 !important;
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
    border-left: 4px solid var(--primary);
    border-radius: 0 8px 8px 0;
    padding: 1.2rem 1.4rem;
    background: var(--bg-surface);
    border-top: 1px solid var(--border);
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    margin-bottom: 1rem;
    box-shadow: var(--shadow-2);
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
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-glow) !important;
    outline: none !important;
}

/* ===== 标签文字 ===== */
.stTextInput label, .stTextArea label, .stSelectbox label,
.stRadio label, .stFileUploader label {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

/* ===== 主按钮（Material Blue）===== */
.stButton > button {
    background: var(--primary) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 1.4rem !important;
    font-family: var(--font-body) !important;
    letter-spacing: 0.1px;
    box-shadow: var(--shadow-1) !important;
    transition: background 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    background: var(--primary-dark) !important;
    box-shadow: var(--shadow-3) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
    box-shadow: var(--shadow-1) !important;
}
.stButton > button:disabled {
    background: #dadce0 !important;
    color: var(--text-muted) !important;
    -webkit-text-fill-color: var(--text-muted) !important;
    cursor: not-allowed !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ===== Download 按钮 ===== */
.stDownloadButton > button {
    background: var(--bg-surface) !important;
    color: var(--primary) !important;
    -webkit-text-fill-color: var(--primary) !important;
    border: 1px solid var(--primary) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 1.4rem !important;
    font-family: var(--font-body) !important;
    box-shadow: var(--shadow-1) !important;
    transition: background 0.2s, box-shadow 0.2s !important;
}
.stDownloadButton > button:hover {
    background: var(--primary-light) !important;
    box-shadow: var(--shadow-2) !important;
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
    border-color: var(--primary) !important;
}

/* ===== Radio 按钮 ===== */
.stRadio > div > label {
    color: var(--text-secondary) !important;
    transition: color 0.15s;
}
.stRadio > div > label:hover {
    color: var(--primary) !important;
}
.stRadio > div > label[data-checked="true"] {
    color: var(--primary) !important;
    font-weight: 600 !important;
}

/* ===== Progress bar ===== */
.stProgress > div > div > div {
    background: var(--primary) !important;
    border-radius: 999px !important;
}
.stProgress > div > div {
    background: var(--border) !important;
    border-radius: 999px !important;
}

/* ===== Expander ===== */
.streamlit-expanderHeader {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    box-shadow: var(--shadow-1);
    transition: background 0.2s, box-shadow 0.2s;
}
.streamlit-expanderHeader:hover {
    background: var(--bg-muted) !important;
    box-shadow: var(--shadow-2) !important;
}

/* ===== File uploader ===== */
div[data-testid="stFileUploader"] > div { border: none !important; }

/* section 强制 flex 横排，按钮在左 */
div[data-testid="stFileUploader"] section,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 1.5rem !important;
    padding: 1.2rem 1.5rem !important;
    background: var(--bg-surface) !important;
    border: 1.5px dashed var(--border) !important;
    border-radius: 10px !important;
    box-shadow: var(--shadow-1);
    transition: border-color 0.2s, background 0.2s;
}
div[data-testid="stFileUploader"] section:hover,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--primary) !important;
    background: var(--primary-light) !important;
}

/* 隐藏 presentation 层多余按钮，只保留 dropzone 内的那个 */
div[data-testid="stFileUploader"] div[role="presentation"] > button {
    display: none !important;
}

/* 按钮放最左：order -1 */
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
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.4rem !important;
    box-shadow: var(--shadow-1) !important;
}
div[data-testid="stFileUploader"] section > button:hover,
div[data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"]:hover {
    background: var(--primary-dark) !important;
}

/* 格式说明 div 在右 */
div[data-testid="stFileUploader"] section > div,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div {
    flex: 1 !important;
    order: 0 !important;
    text-align: left !important;
}

/* 隐藏"将文件拖放到此处"文字，只保留浏览文件按钮；排除按钮内 span */
div[data-testid="stFileUploader"] section > div > span:not(button span),
div[data-testid="stFileUploader"] section > div > small,
div[data-testid="stFileUploader"] section > div > p:first-child,
div[data-testid="stFileUploaderDropzone"] > div > span:not(button span),
div[data-testid="stFileUploaderDropzone"] > div > small {
    display: none !important;
}
/* 确保按钮内 span/文字可见 */
div[data-testid="stFileUploader"] button span,
div[data-testid="stFileUploader"] button p {
    display: inline !important;
    visibility: visible !important;
    color: #ffffff !important;
}

/* ===== h1/h2/h3 标题 ===== */
h1, h2, h3 {
    font-family: var(--font-body) !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    background: none !important;
    letter-spacing: -0.2px;
}

/* ===== 公众号定位选择器标签 ===== */
.selector-label {
    color: var(--text-secondary) !important;
    font-size: 0.85rem;
    font-weight: 500;
    white-space: nowrap;
}
.selector-label-accent {
    color: var(--primary) !important;
}

/* ===== Info/Warning/Success 原生提示框 ===== */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-left-width: 4px !important;
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

/* ===== 滚动条 ===== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-muted); }
::-webkit-scrollbar-thumb {
    background: #bdc1c6;
    border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover { background: #9aa0a6; }

/* ===== 选中文字 ===== */
::selection {
    background: var(--primary-light);
    color: var(--primary);
}

/* ===== 写作风格标签 ===== */
.style-label {
    color: var(--text-secondary) !important;
    font-size: 0.9rem;
    margin-bottom: 6px;
    font-weight: 500;
}

/* ===== Section 卡片容器 ===== */
.section-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    box-shadow: var(--shadow-2);
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
            '<div style="padding-top:8px;color:#5f6368;font-size:0.9rem;">📌 公众号定位</div>',
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

    # 写作风格配置（文章级，每次处理前选择）
    st.divider()
    st.markdown('<div style="color:#5f6368;font-size:0.9rem;margin-bottom:6px;">🎨 写作风格</div>', unsafe_allow_html=True)
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
