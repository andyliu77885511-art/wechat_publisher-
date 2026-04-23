"""
config.py — 统一配置管理
优先从 Streamlit Secrets 读取，其次从环境变量/.env 读取
"""

import os
from dotenv import load_dotenv

load_dotenv()

# 兼容 Streamlit Cloud Secrets
try:
    import streamlit as st
    def _get(key, default=""):
        try:
            return st.secrets[key]
        except Exception:
            return os.getenv(key, default)
except Exception:
    def _get(key, default=""):
        return os.getenv(key, default)


# ===== API 密钥 =====
OPENAI_API_KEY: str = _get("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY: str = _get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = _get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# ===== 微信公众号 =====
WX_APP_ID: str = _get("WX_APP_ID", "")
WX_APP_SECRET: str = _get("WX_APP_SECRET", "")
WX_TOKEN_URL: str = "https://api.weixin.qq.com/cgi-bin/token"
WX_UPLOAD_IMG_URL: str = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
WX_ADD_NEWS_URL: str = "https://api.weixin.qq.com/cgi-bin/draft/add"
WX_FREE_PUBLISH_URL: str = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"

# ===== 本地文件存储 =====
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR: str = os.path.join(BASE_DIR, _get("UPLOAD_DIR", "uploads"))
OUTPUT_DIR: str = os.path.join(BASE_DIR, _get("OUTPUT_DIR", "outputs"))
DB_PATH: str = os.path.join(BASE_DIR, _get("DB_PATH", "wechat_publisher.db"))

# ===== 上传限制 =====
ALLOWED_AUDIO_TYPES: list = ["mp3", "mp4", "m4a", "wav", "avi", "mov", "mkv", "flv", "wmv"]
ALLOWED_FILE_TYPES: list = ["mp3", "mp4", "m4a", "wav", "avi", "mov", "mkv", "flv", "wmv", "pdf", "txt", "docx", "md"]
MAX_FILE_SIZE_MB: int = 500  # 单文件上限（MB）

# ===== 文章生成参数 =====
ARTICLE_MIN_WORDS: int = 1200
ARTICLE_MAX_WORDS: int = 2000
DEEPSEEK_MODEL: str = "deepseek-chat"

# ===== 两阶段调用超时（秒）=====
STAGE1_TIMEOUT: int = 15   # 生成领域风格 prompt
STAGE2_TIMEOUT: int = 60   # 生成最终文章

# ===== 公众号定位与风格配置 =====
CATEGORY_LIST: list = ["财经", "科技", "生活方式", "教育", "职场"]
STYLE_LIST: list = ["严肃专业", "轻松幽默", "深度分析", "故事叙述"]
DEFAULT_CATEGORY: str = "财经"
DEFAULT_STYLE: str = "深度分析"

# ===== 财经写作 System Prompt（精心设计，参考 CTO 方案）=====
FINANCE_STYLE_PROMPT: str = """你是国内顶级财经公众号的专业写手，有多年36氪、吴晓波频道、虎嗅、晚点LatePost等一线财经媒体的撰稿经验。同时深谙「作手新一」「方新侠」「佛总晚评」「牛弹琴」「猫笔刀」等头部财经账号的写作精髓。

## 标题规则（必须严格遵守）
1. 数字冲击：标题必须包含具体数字或比例，如"3000亿""80%暴跌"
2. 反常识/悬念感：制造认知冲突，如"这个行业一年蒸发3000亿，却有人在悄悄逆袭"
3. 简洁口语：控制在12-20字，口语化有情绪感，像在跟读者说话
4. 禁止：副标题拼接、括号注释、"分析""解读""报告""深度"等词
5. 优秀示例："今天这波，要变天了"、"A股，终于等来这个信号"、"散户都在问的问题，我来说清楚"

## 文章开头（前3句必须有张力）
1. 场景钩子：从一个具体场景或现象切入
2. 反问/矛盾：直接抛出反常识的问题
3. 范例：「所有人都以为XX是下一个风口，但数据告诉你，这可能是最大的陷阱。」

## 正文结构（四段式黄金法则）
1. 问题抛出（300字内）：用数据和事实说清楚当前发生了什么
2. 数据支撑（500字内）：行业报告、公司财报、第三方数据佐证
3. 深层分析（800字内）：为什么发生、背后逻辑、产业链影响
4. 结论/预判（300字内）：未来趋势预测、给读者的行动建议

## 语气要求
- 专业但不晦涩：不堆砌术语，必须用普通人听得懂的话
- 有观点有立场：不骑墙，必须有明确的态度倾向
- 数据驱动：每个观点必须有数据或案例支撑，严禁编造数据
- 节奏感强：段落间有逻辑衔接，层层递进

## 财经专有名词
准确保留：A股、北向资金、LPR、CPI、ETF、沪深300、创业板等，所有数字百分比日期必须与原文一致

## 输出格式
- 标题单独一行（不加 # 符号）
- 正文用空行分段，小标题加粗（**小标题**）
- 字数：正文不少于1200字，如内容不足请扩充细节、背景、分析
- 文章开头注明：「本文整理自X月X日直播/视频内容」
- 文末风险提示：「以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。」
- 严禁出现：「一定涨」「必须买」「稳赚」「保本」等绝对化用语
- 不使用 Markdown 列表符号"""

# 兼容旧代码引用
FINANCE_SYSTEM_PROMPT: str = FINANCE_STYLE_PROMPT

# ===== 写作风格语气指令映射 =====
STYLE_INSTRUCTIONS: dict = {
    "严肃专业": "语言克制，逻辑严密，数据支撑，少用感叹号，多用「研究表明」「数据显示」等表述。",
    "轻松幽默": "口语化，有梗，短句多，像朋友在聊天，可以用「哈哈」「说实话」等口头禅，适度调侃但不失专业。",
    "深度分析": "层层递进，有框架，有反驳，有结论，每个观点都追问「为什么」，给出深层逻辑。",
    "故事叙述": "用具体场景和人物开头，情节感强，道理藏在故事里，结尾才点出核心观点。",
}

# ===== 其他定位的 Meta Prompt 模板（第一阶段：生成领域风格指令）=====
META_PROMPT_STAGE1: str = """你是公众号写作风格专家，现在需要你为【{position_name}】领域生成一套详细的写作风格指令。

参考该领域顶级公众号的写作特征，生成的指令将直接用于指导 AI 写作，请确保具体、可操作。

输出要求：
1. 标题规则：该领域优质文章的标题写法（字数、句式、情绪感）
2. 开头技巧：如何在前3句话抓住读者
3. 正文结构：该领域最适合的内容组织方式
4. 语气要求：与读者的沟通风格
5. 输出格式：字数、段落、小标题等

请直接输出风格指令文本，不要加解释性说明，格式参考：

你是【{position_name}】领域顶级公众号的专业写手...（继续写出完整的风格指令）"""

# ===== 第二阶段 User Prompt 模板（财经和其他定位通用）=====
def build_user_prompt(transcript: str, category: str) -> str:
    """根据定位构建 user prompt"""
    if category == "财经":
        return f"请将以下音视频转录稿整理为一篇财经公众号文章：\n\n{transcript}"
    else:
        return f"请将以下内容改写成一篇{category}领域的高质量公众号文章：\n\n{transcript}"


def build_stage2_system_prompt(style_prompt: str, style: str) -> str:
    """
    组合定位风格 prompt + 写作风格指令，生成最终的 system prompt
    """
    style_instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS[DEFAULT_STYLE])
    return f"""{style_prompt}

## 写作风格要求（叠加在上述风格之上）
{style_instruction}

## 输出格式
- 标题单独一行（不加 # 符号）
- 正文用空行分段，小标题加粗（**小标题**）
- 字数：正文不少于1200字
- 不使用 Markdown 列表符号"""


def get_system_prompt(category: str, style: str) -> str:
    """
    获取 system prompt（单阶段模式，供内部补充调用使用）
    财经：直接返回硬编码 prompt
    其他：返回通用模板（两阶段模式下此函数仅供补充段落时调用）
    """
    if category == "财经":
        return FINANCE_STYLE_PROMPT

    style_instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS[DEFAULT_STYLE])
    return f"""你是一个{category}领域的顶级公众号作者。请先分析该领域最优秀公众号的写作特征，然后按照这些特征，将以下内容改写成一篇高质量的公众号文章。

写作风格要求：{style_instruction}

输出格式：
- 标题单独一行（12-20字，口语化有情绪感，不超过20字）
- 正文用空行分段，小标题加粗（**小标题**）
- 字数：正文不少于1200字
- 不使用 Markdown 列表符号"""


# ===== Streamlit 页面配置 =====
PAGE_TITLE: str = "公众号自动发布工具"
PAGE_ICON: str = "📰"
PAGE_VERSION: str = "MVP v1.2"


def validate_config() -> dict:
    """检查必要配置是否存在，返回缺失项列表"""
    missing = []
    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")
    if not WX_APP_ID:
        missing.append("WX_APP_ID")
    # WX_APP_SECRET 暂不启用，微信发布功能保留但不强制检查
    return {"ok": len(missing) == 0, "missing": missing}
