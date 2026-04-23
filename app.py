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
/* ===== 动画 Keyframes ===== */
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-24px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes slideInUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-glow {
    0%   { box-shadow: 0 0 0 0 rgba(108, 99, 255, 0.55); }
    70%  { box-shadow: 0 0 0 12px rgba(108, 99, 255, 0); }
    100% { box-shadow: 0 0 0 0 rgba(108, 99, 255, 0); }
}
@keyframes borderPulse {
    0%   { border-color: #6C63FF; box-shadow: 0 0 0 0 rgba(108,99,255,0.4); }
    50%  { border-color: #1CB5E0; box-shadow: 0 0 16px 4px rgba(28,181,224,0.35); }
    100% { border-color: #6C63FF; box-shadow: 0 0 0 0 rgba(108,99,255,0.4); }
}
@keyframes shimmer {
    0%   { background-position: -400px 0; }
    100% { background-position: 400px 0; }
}

/* ===== 全局背景 ===== */
.stApp {
    background: linear-gradient(135deg, #0F0C29 0%, #1a1040 40%, #0d2137 100%) !important;
    min-height: 100vh;
}
.main .block-container {
    max-width: 760px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* ===== Header 淡入 ===== */
.app-header {
    animation: fadeInDown 0.7s ease both;
    background: linear-gradient(90deg, #6C63FF, #1CB5E0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-bottom: 0.2rem;
}
.app-subtitle {
    animation: fadeInDown 0.9s ease both;
    color: rgba(255,255,255,0.45);
    font-size: 0.85rem;
    margin-top: 0;
}

/* ===== 分隔线 ===== */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(108,99,255,0.5), transparent) !important;
    margin: 1.5rem 0 !important;
}

/* ===== 步骤指示器（胶囊/标签样式）===== */
.step-capsule-done {
    display: inline-block;
    background: linear-gradient(90deg, #6C63FF, #1CB5E0);
    color: #fff !important;
    border-radius: 999px;
    padding: 4px 16px;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.3px;
    animation: slideInUp 0.4s ease both;
}
.step-capsule-active {
    display: inline-block;
    background: linear-gradient(90deg, #6C63FF, #1CB5E0);
    color: #fff !important;
    border-radius: 999px;
    padding: 4px 16px;
    font-size: 0.82rem;
    font-weight: 700;
    animation: pulse-glow 1.6s infinite, slideInUp 0.4s ease both;
    box-shadow: 0 0 0 0 rgba(108, 99, 255, 0.55);
}
.step-capsule-wait {
    display: inline-block;
    background: rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.35) !important;
    border-radius: 999px;
    padding: 4px 16px;
    font-size: 0.82rem;
    font-weight: 500;
    border: 1px solid rgba(255,255,255,0.12);
}

/* ===== 上传区卡片 ===== */
.upload-box {
    border: 2px dashed #6C63FF;
    border-radius: 20px;
    padding: 3.5rem 2rem;
    text-align: center;
    background: linear-gradient(135deg, rgba(108,99,255,0.12) 0%, rgba(28,181,224,0.08) 100%);
    margin: 1rem 0;
    transition: all 0.3s ease;
    animation: slideInUp 0.5s ease both;
    animation-delay: 0.1s;
}
.upload-box:hover {
    animation: borderPulse 1.5s ease infinite;
    background: linear-gradient(135deg, rgba(108,99,255,0.2) 0%, rgba(28,181,224,0.15) 100%);
}
.upload-icon {
    font-size: 3.2rem;
    display: block;
    margin-bottom: 0.5rem;
    filter: drop-shadow(0 0 12px rgba(108,99,255,0.7));
}
.upload-title {
    font-size: 1.15rem;
    font-weight: 700;
    background: linear-gradient(90deg, #6C63FF, #1CB5E0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
}
.upload-hint {
    color: rgba(255,255,255,0.45);
    font-size: 0.85rem;
}

/* ===== 子步骤状态 ===== */
.step-done  { color: #43E97B; font-weight: 600; }
.step-active { color: #6C63FF; font-weight: 600; }
.step-wait  { color: rgba(255,255,255,0.3); }

/* ===== 提示框 ===== */
.warn-box {
    background: linear-gradient(135deg, rgba(251,140,0,0.15), rgba(251,140,0,0.05));
    border: 1px solid rgba(251,140,0,0.5);
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

/* ===== 文章编辑区：左彩条 ===== */
.editor-card {
    border-left: 4px solid transparent;
    border-image: linear-gradient(180deg, #6C63FF, #1CB5E0) 1;
    border-radius: 0 12px 12px 0;
    padding: 1.2rem 1.5rem;
    background: rgba(255,255,255,0.04);
    margin-bottom: 1rem;
    animation: slideInUp 0.5s ease both;
}

/* ===== 输入框高亮线条 ===== */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(108,99,255,0.3) !important;
    border-radius: 10px !important;
    color: #fff !important;
    transition: border-color 0.25s, box-shadow 0.25s;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #6C63FF !important;
    box-shadow: 0 2px 0 0 #6C63FF, 0 0 12px rgba(108,99,255,0.3) !important;
    outline: none !important;
}

/* ===== 按钮：渐变 + hover 上浮 ===== */
.stButton > button {
    background: linear-gradient(90deg, #6C63FF, #1CB5E0) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 1.5rem !important;
    box-shadow: 0 4px 18px rgba(108,99,255,0.35) !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 8px 28px rgba(108,99,255,0.55) !important;
}
.stButton > button:active {
    transform: translateY(0) scale(0.98) !important;
    box-shadow: 0 2px 8px rgba(108,99,255,0.3) !important;
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

/* ===== 下载按钮 ===== */
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
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 8px 28px rgba(67,233,123,0.5) !important;
}

/* ===== 标签/Caption 颜色 ===== */
.stCaption, label, .stMarkdown p {
    color: rgba(255,255,255,0.65) !important;
}

/* ===== 进度条 ===== */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #6C63FF, #1CB5E0) !important;
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
    background: rgba(108,99,255,0.07) !important;
    border: 1.5px dashed rgba(108,99,255,0.5) !important;
    border-radius: 12px !important;
}

/* ===== subheader 样式 ===== */
h2, h3 {
    background: linear-gradient(90deg, #ffffff, rgba(255,255,255,0.7));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800 !important;
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

    # 按钮始终显示，未上传时灰色不可点，上传成功后蓝色可点
    if st.button("🚀 开始处理", type="primary", use_container_width=True, disabled=not file_ready):
        file_path, file_type = save_uploaded_file(uploaded)
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

            result = generate_article(transcript)

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

            # Step 2.2: 语音转录
            sub_steps[1]["status"] = "active"
            status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
            progress_placeholder.progress(0.3)

            transcript = transcribe(Path(audio_path))
            update_material(st.session_state.material_id, transcript=transcript, status="transcribed", duration=duration)

            sub_steps[1]["status"] = "done"
            st.session_state.transcript = transcript

        # Step 2.3: AI 生成文章
        sub_steps[2]["status"] = "active"
        status_placeholder.markdown(render_sub_steps(sub_steps), unsafe_allow_html=True)
        progress_placeholder.progress(0.6)

        result = generate_article(transcript)

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
