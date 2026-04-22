"""
config.py — 统一配置管理
所有配置从环境变量读取，提供默认值，确保缺少非必要配置时不崩溃
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ===== API 密钥 =====
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# ===== 微信公众号 =====
WX_APP_ID: str = os.getenv("WX_APP_ID", "")
WX_APP_SECRET: str = os.getenv("WX_APP_SECRET", "")
WX_TOKEN_URL: str = "https://api.weixin.qq.com/cgi-bin/token"
WX_UPLOAD_IMG_URL: str = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
WX_ADD_NEWS_URL: str = "https://api.weixin.qq.com/cgi-bin/draft/add"
WX_FREE_PUBLISH_URL: str = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"

# ===== 本地文件存储 =====
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR: str = os.path.join(BASE_DIR, os.getenv("UPLOAD_DIR", "uploads"))
OUTPUT_DIR: str = os.path.join(BASE_DIR, os.getenv("OUTPUT_DIR", "outputs"))
DB_PATH: str = os.path.join(BASE_DIR, os.getenv("DB_PATH", "wechat_publisher.db"))

# ===== 上传限制 =====
ALLOWED_AUDIO_TYPES: list = ["mp3", "mp4", "m4a", "wav"]
MAX_FILE_SIZE_MB: int = 500  # 单文件上限（MB）

# ===== 文章生成参数 =====
ARTICLE_MIN_WORDS: int = 1200
ARTICLE_MAX_WORDS: int = 2000
DEEPSEEK_MODEL: str = "deepseek-chat"

# ===== 财经写作 System Prompt =====
FINANCE_SYSTEM_PROMPT: str = """你是一位专业的财经内容编辑，擅长将音视频转录稿整理为高质量的公众号文章。

写作规范：
1. 识别并准确保留财经专有名词：A股、北向资金、LPR、CPI、ETF、沪深300、创业板等
2. 文中出现的所有具体数字、百分比、日期必须与原文一致，严禁编造数据
3. 过滤口语化表达、重复内容、离题内容
4. 语气专业但通俗易懂，面向普通投资者
5. 结构：标题 + 导语（2-3句） + 正文（3-5个小标题分段） + 结语（1段）
6. 字数：1200-2000字
7. 在文章开头注明来源时效，格式：「本文整理自X月X日直播/视频内容」
8. 文章末尾必须添加风险提示：「以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。」
9. 严禁出现绝对化用语：「一定涨」「必须买」「稳赚」「保本」等

输出格式要求：
- 标题单独一行（不加 # 符号）
- 正文用空行分段
- 小标题加粗（**小标题**）
- 不使用 Markdown 列表符号"""

# ===== Streamlit 页面配置 =====
PAGE_TITLE: str = "公众号自动发布工具"
PAGE_ICON: str = "📰"
PAGE_VERSION: str = "MVP v1.0"


def validate_config() -> dict:
    """检查必要配置是否存在，返回缺失项列表"""
    missing = []
    # OPENAI_API_KEY 为可选项，项目使用 DeepSeek
    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")
    if not WX_APP_ID:
        missing.append("WX_APP_ID")
    if not WX_APP_SECRET:
        missing.append("WX_APP_SECRET")
    return {"ok": len(missing) == 0, "missing": missing}
