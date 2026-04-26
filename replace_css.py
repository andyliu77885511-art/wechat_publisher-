#!/usr/bin/env python3
import re

# 读取完整 app.py
with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 新的 openclaw.ai 风格 CSS（完整版）
new_css_block = '''# ── openclaw.ai 风格 CSS ─────────────────────────────────────────────────────────
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
'''

# 替换 CSS 部分（从 "# ── 自定义样式" 到 "# ── 初始化" 之间）
pattern = r'# ── 自定义样式.*?(?=# ── 初始化)'
new_content = re.sub(pattern, new_css_block + '\n\n', content, flags=re.DOTALL)

# 写回文件
with open("app.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("✅ CSS 替换完成")
