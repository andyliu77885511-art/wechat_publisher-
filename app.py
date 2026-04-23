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

# ── 自定义样式 ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #F5F7FA; }
    .main .block-container { max-width: 730px; padding-top: 2rem; }
    .upload-box {
        border: 2px dashed #1677FF;
        border-radius: 12px;
        padding: 3rem 2rem;
        text-align: center;
        background: #F0F5FF;
        margin: 1rem 0;
    }
    .step-done { color: #43A047; font-weight: 600; }
    .step-active { color: #1677FF; font-weight: 600; }
    .step-wait { color: #9E9E9E; }
    .warn-box {
        background: #FFF3E0;
        border: 1px solid #FB8C00;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        color: #E65100;
    }
    .success-box {
        background: #E8F5E9;
        border: 1px solid #43A047;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        color: #1B5E20;
    }
    .error-box {
        background: #FFEBEE;
        border: 1px solid #E53935;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        color: #B71C1C;
    }
    div[data-testid="stFileUploader"] > div { border: none !important; }
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
    """渲染横向进度指示器"""
    # BUG-003 FIX: 使用 next() 带默认值查找，防止非法 step 值 crash
    current_idx = next((i for i, s in enumerate(steps_list) if s[0] == current_step_key), 0)
    cols = st.columns(len(steps_list))
    for i, (step_key, step_label) in enumerate(steps_list):
        with cols[i]:
            if i < current_idx:
                st.markdown(f'<span class="step-done">✓ {step_label}</span>', unsafe_allow_html=True)
            elif i == current_idx:
                st.markdown(f'<span class="step-active">● {step_label}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="step-wait">○ {step_label}</span>', unsafe_allow_html=True)


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
    st.title(f"{config.PAGE_ICON} {config.PAGE_TITLE}")
with col_ver:
    st.caption(config.PAGE_VERSION)

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
        '<p style="font-size:1.2rem;color:#1677FF;">📁 拖拽文件到此处，或点击下方按钮选择</p>'
        f'<p style="color:#666;margin-top:0.5rem;">支持格式：{", ".join(config.ALLOWED_AUDIO_TYPES)} | '
        f'最大 {config.MAX_FILE_SIZE_MB}MB</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "选择文件",
        type=config.ALLOWED_AUDIO_TYPES,
        label_visibility="collapsed",
    )

    file_ready = False
    file_size_ok = True

    if uploaded:
        file_size_mb = uploaded.size / (1024 * 1024)
        st.info(f"已选择：{uploaded.name}（{file_size_mb:.1f} MB）")
        if file_size_mb > config.MAX_FILE_SIZE_MB:
            st.markdown(
                f'<div class="error-box">文件大小超过限制（{config.MAX_FILE_SIZE_MB}MB），请压缩后重试。</div>',
                unsafe_allow_html=True,
            )
            file_size_ok = False
        else:
            file_ready = True

    if st.button("开始处理", type="primary", use_container_width=True, disabled=not file_ready):
        if file_ready:
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

    sub_steps = [
        {"label": "提取音频", "status": "wait"},
        {"label": "语音转录", "status": "wait"},
        {"label": "AI 生成文章", "status": "wait"},
        {"label": "保存结果", "status": "wait"},
    ]

    try:
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


# ═════════════════════════════════════════