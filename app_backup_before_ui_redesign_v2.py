"""
app.py — 公众号自动发布工具 Streamlit 主入口
流程：上传文件 -> 转录/生成 -> 预览编辑 -> 发布确认
"""
import streamlit as st
from pathlib import Path
import threading
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

# ── openclaw.ai 风格 CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ===== 动画 Keyframes ===== */
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-20px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes slideInUp {
    from { opacity: 0; transform: translateY(15px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-glow-orange {
    0%   { box-shadow: 0 0 0 0 rgba(255,140,0,0.5); }
    70%  { box-shadow: 0 0 0 10px rgba(255,140,0,0); }
    100% { box-shadow: 0 0 0 0 rgba(255,140,0,0); }
}

/* ===== 全局背景（openclaw.ai 深蓝黑渐变）===== */
.stApp {
    background: linear-gradient(135deg, #0a1628 0%, #1a2332 50%, #0d1b2a 100%) !important;
    min-height: 100vh;
}
.main .block-container {
    max-width: 820px;
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

/* ===== Header 样式（白色简洁）===== */
.app-header {
    animation: fadeInDown 0.6s ease both;
    color: #ffffff;
    font-size: 2.2rem;
    font-weight: 700;
    letter-spacing: -0.8px;
    margin-bottom: 0.3rem;
}
.app-subtitle {
    animation: fadeInDown 0.8s ease both;
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
    border-color: rgba(255,165,0,0.35);
    box-shadow: 0 6px 28px rgba(255,165,0,0.1);
}
.position-card-header {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    margin-bottom: 0.2rem;
}
.position-card-icon {
    font-size: 1.6rem;
    line-height: 1;
    filter: drop-shadow(0 0 6px rgba(255,165,0,0.5));
}
.position-card-title {
    color: #ffffff;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: -0.3px;
    line-height: 1.3;
}
.position-card-sub {
    color: rgba(255,255,255,0.45);
    font-size: 0.8rem;
    font-weight: 400;
    margin-top: 2px;
}
.position-desc-pill {
    display: inline-block;
    background: rgba(255,165,0,0.12);
    border: 1px solid rgba(255,165,0,0.25);
    color: rgba(255,190,80,0.9);
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 0.82rem;
    font-weight: 500;
    line-height: 1.5;
    margin-top: 4px;
    animation: slideInUp 0.3s ease both;
}
.position-label {
    color: rgba(255,255,255,0.65);
    font-size: 0.92rem;
    font-weight: 500;
    margin-bottom: 0.8rem;
    display: block;
}

/* ===== 步骤指示器（圆点风格，橙色激活）===== */
.step-capsule-done {
    display: inline-block;
    background: rgba(67,233,123,0.2);
    color: #43E97B !important;
    border: 1px solid rgba(67,233,123,0.4);
    border-radius: 999px;
    padding: 4px 16px;
    font-size: 0.82rem;
    font-weight: 600;
    animation: slideInUp 0.4s ease both;
}
.step-capsule-active {
    display: inline-block;
    background: linear-gradient(90deg, #FF8C00, #FFA500);
    color: #fff !important;
    border-radius: 999px;
    padding: 4px 16px;
    font-size: 0.82rem;
    font-weight: 700;
    animation: pulse-glow-orange 1.5s infinite, slideInUp 0.4s ease both;
}
.step-capsule-wait {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    color: rgba(255,255,255,0.3) !important;
    border-radius: 999px;
    padding: 4px 16px;
    font-size: 0.82rem;
    font-weight: 500;
    border: 1px solid rgba(255,255,255,0.08);
}

/* ===== 上传区卡片 ===== */
.upload-box {
    border: 2px dashed rgba(255,165,0,0.4);
    border-radius: 20px;
    padding: 3.5rem 2rem;
    text-align: center;
    background: linear-gradient(135deg, rgba(255,140,0,0.08) 0%, rgba(255,165,0,0.04) 100%);
    margin: 1rem 0;
    transition: all 0.3s ease;
    animation: slideInUp 0.5s ease both;
}
.upload-box:hover {
    border-color: rgba(255,165,0,0.6);
    background: linear-gradient(135deg, rgba(255,140,0,0.12) 0%, rgba(255,165,0,0.08) 100%);
    box-shadow: 0 4px 20px rgba(255,140,0,0.1);
}
.upload-icon {
    font-size: 3.2rem;
    display: block;
    margin-bottom: 0.5rem;
    filter: drop-shadow(0 0 8px rgba(255,165,0,0.5));
}
.upload-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #FFA500;
    margin-bottom: 0.3rem;
}
.upload-hint {
    color: rgba(255,255,255,0.45);
    font-size: 0.85rem;
}

/* ===== 子步骤状态 ===== */
.step-done  { color: #43E97B; font-weight: 600; }
.step-active { color: #FFA500; font-weight: 600; }
.step-wait  { color: rgba(255,255,255,0.3); }

/* ===== 提示框（橙色 warning）===== */
.warn-box {
    background: linear-gradient(135deg, rgba(255,140,0,0.15), rgba(255,140,0,0.05));
    border: 1px solid rgba(255,140,0,0.5);
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin: 1rem 0;
    color: #FFB74D;
    animation: slideInUp 0.4s ease both;
}
.success-box {
    background: linear-gradient(135deg, rgba(67,233,123,0.15), rgba(67,233,123,0.05));
    border: 1px solid rgba(67,233,123,0.4);
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin: 1rem 0;
    color: #43E97B;
    animation: slideInUp 0.4s ease both;
}
.error-box {
    background: linear-gradient(135deg, rgba(229,57,53,0.15), rgba(229,57,53,0.05));
    border: 1px solid rgba(229,57,53,0.4);
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin: 1rem 0;
    color: #EF9A9A;
    animation: slideInUp 0.4s ease both;
}

/* ===== 文章编辑区：左彩条（橙色）===== */
.editor-card {
    border-left: 4px solid #FFA500;
    border-radius: 0 12px 12px 0;
    padding: 1.2rem 1.5rem;
    background: rgba(255,255,255,0.04);
    margin-bottom: 1rem;
    animation: slideInUp 0.5s ease both;
}

/* ===== 输入框高亮线条（橙色 focus）===== */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #fff !important;
    transition: border-color 0.25s, box-shadow 0.25s;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stSelectbox > div > div > select:focus {
    border-color: #FFA500 !important;
    box-shadow: 0 2px 0 0 #FFA500, 0 0 12px rgba(255,165,0,0.3) !important;
    outline: none !important;
}

/* ===== 按钮：橙色渐变 + hover 上浮 ===== */
.stButton > button {
    background: linear-gradient(90deg, #FF8C00, #FFA500) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 1.5rem !important;
    box-shadow: 0 4px 18px rgba(255,140,0,0.35) !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 6px 24px rgba(255,140,0,0.5) !important;
}
.stButton > button:active {
    transform: translateY(0) scale(0.98) !important;
    box-shadow: 0 2px 8px rgba(255,140,0,0.3) !important;
}
/* 次要按钮（← 上一步等）稍微暗一些 */
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.08) !important;
    box-shadow: none !important;
    color: rgba(255,255,255,0.7) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.14) !important;
    box-shadow: none !important;
}

/* ===== 下载按钮（绿色系）===== */
.stDownloadButton > button {
    background: linear-gradient(90deg, #43E97B, #38F9D7) !important;
    color: #0a0a14 !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 18px rgba(67,233,123,0.3) !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease !important;
}
.stDownloadButton > button:hover {
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 6px 24px rgba(67,233,123,0.5) !important;
}

/* ===== 标签/Caption 颜色 ===== */
.stCaption, label, .stMarkdown p {
    color: rgba(255,255,255,0.65) !important;
}

/* ===== 进度条（橙色）===== */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #FF8C00, #FFA500) !important;
    border-radius: 999px !important;
}
.stProgress > div > div {
    background: rgba(255,255,255,0.08) !important;
    border-radius: 999px !important;
}

/* ===== Expander ===== */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.05) !important;
    border-radius: 10px !important;
    color: rgba(255,255,255,0.8) !important;
    font-weight: 600 !important;
}

/* ===== file uploader 边框去除 ===== */
div[data-testid="stFileUploader"] > div { border: none !important; }
div[data-testid="stFileUploader"] section {
    background: rgba(255,140,0,0.05) !important;
    border: 1.5px dashed rgba(255,165,0,0.4) !important;
    border-radius: 12px !important;
}

/* ===== subheader 样式 ===== */
h2, h3 {
    color: #ffffff;
    font-weight: 700 !important;
}

/* ===== info/warning/success Streamlit 原生组件 ===== */
div[data-testid="stAlert"] {
    border-radius: 12px !important;
    border: none !important;
    background: rgba(255,255,255,0.07) !important;
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

# 定位描述映射
_category_desc = {
    "财经": "财经深度分析，覆盖宏观经济、市场趋势、投资见解",
    "科技": "科技资讯与产品评测，聚焦前沿技术与行业动态",
    "生活": "生活方式与消费决策，贴近用户日常需求",
    "教育": "知识传递与学习成长，深度解读教育话题",
    "健康": "健康科普与医疗资讯，严谨专业可信赖",
    "其他": "AI 自动识别领域，两阶段自适应生成最佳风格",
}

# 计算当前状态
_current_in_list = st.session_state.category in config.CATEGORY_LIST
_selector_index = (
    config.CATEGORY_LIST.index(st.session_state.category)
    if _current_in_list
    else config.CATEGORY_LIST.index("其他")
)

# 卡片头部 HTML（图标 + 标题 + 说明）
st.markdown(
    """
    <div class="position-card">
        <div class="position-card-header">
            <span class="position-card-icon">📌</span>
            <div>
                <div class="position-card-title">公众号定位</div>
                <div class="position-card-sub">选择定位以匹配最佳 AI 写作风格</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 选择器行（cols 实现内联布局）
_pc_col_sel, _pc_col_desc = st.columns([2, 3])
with _pc_col_sel:
    selected_category = st.selectbox(
        "公众号定位",
        options=config.CATEGORY_LIST,
        index=_selector_index,
        label_visibility="collapsed",
        key="category_selector",
    )

with _pc_col_desc:
    _desc_text = _category_desc.get(
        selected_category if selected_category != "其他" else "其他",
        "AI 自动适配最佳写作风格"
    )
    if selected_category != "其他":
        _desc_text = _category_desc.get(selected_category, "AI 自动适配最佳写作风格")
    st.markdown(
        f'<div class="position-desc-pill">{_desc_text}</div>',
        unsafe_allow_html=True,
    )

# 自定义定位输入框
if selected_category == "其他":
    _custom_val = "" if _current_in_list else st.session_state.category
    custom_category = st.text_input(
        "输入自定义定位名称",
        value=_custom_val,
        placeholder="例如：母婴、健身、旅游...",
        label_visibility="visible",
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
        # 上传进度反馈（threading 异步保存 + 精确倒计时）
        import threading as _threading
        _file_size_mb = uploaded.size / (1024 * 1024)
        # 按 2MB/s 估算，最少 1 秒
        _est_sec = max(1, int(_file_size_mb / 2))
        _upload_bar = st.progress(0, text="📤 正在上传文件，请稍候...")
        _upload_status = st.empty()

        # 在后台线程做文件保存 IO
        _save_result = [None, None]   # [file_path, file_type]
        _save_error  = [None]
        _save_done   = _threading.Event()

        def _do_save():
            try:
                _save_result[0], _save_result[1] = save_uploaded_file(uploaded)
            except Exception as _e:
                _save_error[0] = _e
            finally:
                _save_done.set()

        _save_thread = _threading.Thread(target=_do_save, daemon=True)
        _save_thread.start()

        # 主线程动态更新进度条（每 0.3s 刷新一次）
        _elapsed = 0.0
        _tick_interval = 0.3
        while not _save_done.wait(timeout=_tick_interval):
            _elapsed += _tick_interval
            _pct = min(_elapsed / max(_est_sec, 1) * 0.92, 0.92)  # 最多到 92%
            _remain = max(0, _est_sec - int(_elapsed))
            if _remain > 0:
                _remain_str = f"预计还需 {_remain} 秒"
            else:
                _remain_str = "即将完成..."
            _upload_bar.progress(_pct, text=f"📤 正在上传文件...（{_remain_str}）")

        _save_thread.join()

        if _save_error[0]:
            st.error(f"文件保存失败：{_save_error[0]}")
            st.stop()

        file_path, file_type = _save_result[0], _save_result[1]
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

            # Step 2.2: AI 生成文章（跳过转录步骤，threading + 预估剩余时间）
            sub_steps[1]["status"] = "active"
            status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
            progress_placeholder.progress(0.5)

            _ai_result  = [None]
            _ai_error   = [None]
            _ai_done    = threading.Event()
            _category_snap = st.session_state.category
            _style_snap    = st.session_state.writing_style
            # 非财经定位首次调用需两阶段（预估约75s），财经约45s
            _ai_est_sec = 75 if _category_snap != "财经" else 45

            def _do_generate_doc():
                try:
                    _ai_result[0] = generate_article(
                        transcript,
                        category=_category_snap,
                        style=_style_snap,
                    )
                except Exception as _e:
                    _ai_error[0] = _e
                finally:
                    _ai_done.set()

            _ai_thread = threading.Thread(target=_do_generate_doc, daemon=True)
            _ai_thread.start()

            _ai_bar = st.empty()
            _ai_tip = st.empty()
            _ai_elapsed = 0.0
            _ai_tick = 0.8
            _ai_tips = [
                f"🤖 AI 正在为「{_category_snap}」定位生成文章...",
                f"🤖 AI 正在思考，定位：{_category_snap} × 风格：{_style_snap}",
                "🤖 文章生成需要 30-75 秒，请稍候...",
                "🤖 快好了，AI 正在润色收尾...",
            ]
            _ai_tip_idx = 0
            while not _ai_done.wait(timeout=_ai_tick):
                _ai_elapsed += _ai_tick
                _ai_pct = min(0.5 + (_ai_elapsed / _ai_est_sec) * 0.45, 0.95)
                progress_placeholder.progress(_ai_pct)
                _remain_ai = max(0, _ai_est_sec - int(_ai_elapsed))
                _tip_text = _ai_tips[min(_ai_tip_idx // 5, len(_ai_tips) - 1)]
                if _remain_ai > 0:
                    _remain_ai_str = f"预计还需 {_remain_ai} 秒"
                else:
                    _remain_ai_str = "即将完成..."
                _ai_bar.progress(
                    min(_ai_elapsed / _ai_est_sec, 0.98),
                    text=f"{_tip_text}（{_remain_ai_str}）"
                )
                _ai_tip_idx += 1

            _ai_thread.join()
            _ai_bar.empty()
            _ai_tip.empty()

            if _ai_error[0]:
                raise _ai_error[0]

            result = _ai_result[0]
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

        # Step 2.3: AI 生成文章（threading + 预估剩余时间）
        sub_steps[2]["status"] = "active"
        status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
        progress_placeholder.progress(0.6)

        _ai_result2  = [None]
        _ai_error2   = [None]
        _ai_done2    = threading.Event()
        _category_snap2 = st.session_state.category
        _style_snap2    = st.session_state.writing_style
        _ai_est_sec2 = 75 if _category_snap2 != "财经" else 45

        def _do_generate_av():
            try:
                _ai_result2[0] = generate_article(
                    transcript,
                    category=_category_snap2,
                    style=_style_snap2,
                )
            except Exception as _e:
                _ai_error2[0] = _e
            finally:
                _ai_done2.set()

        _ai_thread2 = threading.Thread(target=_do_generate_av, daemon=True)
        _ai_thread2.start()

        _ai_bar2 = st.empty()
        _ai_elapsed2 = 0.0
        _ai_tick2 = 0.8
        _ai_tips2 = [
            f"🤖 AI 正在为「{_category_snap2}」定位生成文章...",
            f"🤖 AI 正在思考，定位：{_category_snap2} × 风格：{_style_snap2}",
            "🤖 文章生成需要 30-75 秒，请稍候...",
            "🤖 快好了，AI 正在润色收尾...",
        ]
        _ai_tip2_idx = 0
        while not _ai_done2.wait(timeout=_ai_tick2):
            _ai_elapsed2 += _ai_tick2
            _ai_pct2 = min(0.6 + (_ai_elapsed2 / _ai_est_sec2) * 0.35, 0.95)
            progress_placeholder.progress(_ai_pct2)
            _remain_ai2 = max(0, _ai_est_sec2 - int(_ai_elapsed2))
            _tip_text2 = _ai_tips2[min(_ai_tip2_idx // 5, len(_ai_tips2) - 1)]
            if _remain_ai2 > 0:
                _remain_ai2_str = f"预计还需 {_remain_ai2} 秒"
            else:
                _remain_ai2_str = "即将完成..."
            _ai_bar2.progress(
                min(_ai_elapsed2 / _ai_est_sec2, 0.98),
                text=f"{_tip_text2}（{_remain_ai2_str}）"
            )
            _ai_tip2_idx += 1

        _ai_thread2.join()
        _ai_bar2.empty()

        if _ai_error2[0]:
            raise _ai_error2[0]

        result = _ai_result2[0]
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
        wx_secret_missing = not config.WX_APP_SECRET
        if wx_secret_missing:
            st.caption("微信发布功能暂未开放")
        if st.button("确认发布 →", type="primary", use_container_width=True, disabled=wx_secret_missing):
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
# 步骤 4：发布确认页
# ══════════════════════════════════════════════════════════════════════════════════

elif st.session_state.step == "publish":

    st.subheader("发布确认")

    # 发布功能状态提示
    wx_secret_missing = not config.WX_APP_SECRET

    if wx_secret_missing:
        st.markdown(
            '''<div class="warn-box">
            ⚠️ 微信发布功能暂未开放<br>
            <span style="font-size:0.85rem;opacity:0.8;">
            管理员尚未配置 WX_APP_SECRET，文章无法直接发布到公众号。<br>
            你可以返回上一步下载 .txt 文件，手动发布。
            </span>
            </div>''',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '''<div class="success-box">
            ✓ 微信发布功能已就绪，可发布到公众号。
            </div>''',
            unsafe_allow_html=True,
        )

    # 文章信息摘要
    st.markdown('''<div class="editor-card">''', unsafe_allow_html=True)
    st.markdown(f"**标题：** {st.session_state.article_title or '（未设置）'}")
    wc_publish = word_count(st.session_state.article_content or "")
    st.markdown(f"**字数：** {wc_publish} 字")
    st.markdown('''</div>''', unsafe_allow_html=True)

    st.divider()

    col_back, col_dl = st.columns([1, 1])
    with col_back:
        if st.button("← 返回编辑", use_container_width=True):
            st.session_state.step = "preview"
            st.rerun()
    with col_dl:
        # 提供下载兜底
        dl_title = st.session_state.article_title or "article"
        dl_content = st.session_state.article_content or ""
        txt_content = f"{dl_title}\n\n{dl_content}\n\n---\n以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
        st.download_button(
            "📥 下载 .txt",
            txt_content.encode("utf-8"),
            file_name=f"{dl_title[:30]}.txt",
            mime="text/plain",
            use_container_width=True,
        )
