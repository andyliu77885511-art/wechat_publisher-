# 公众号自动发布工具 — 部署指南

## 环境要求

- Python 3.10+
- ffmpeg（系统级依赖，用于音视频处理）

## 一、环境变量配置

### 1. 复制配置文件

```bash
cp .env.example .env
```

### 2. 编辑 .env 文件

```env
# ── API 密钥 ──────────────────────────────────────────────
# DeepSeek（用于 AI 文章生成）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# ── 微信公众号 ────────────────────────────────────────────
# 在微信公众平台获取
WX_APP_ID=wx_your_appid_here
WX_APP_SECRET=your_app_secret_here

# ── 本地存储（通常不需要修改）──────────────────────────────
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
DB_PATH=wechat_publisher.db
```

### 3. 环境变量说明

| 变量 | 必须 | 说明 |
|------|------|------|
| DEEPSEEK_API_KEY | 是 | DeepSeek API 密钥，文章生成用 |
| DEEPSEEK_BASE_URL | 否 | 默认 `https://api.deepseek.com` |
| WX_APP_ID | 是 | 微信公众号 AppID |
| WX_APP_SECRET | 是 | 微信公众号 AppSecret |
| UPLOAD_DIR | 否 | 上传文件存放目录，默认 `uploads` |
| OUTPUT_DIR | 否 | 输出文件存放目录，默认 `outputs` |
| DB_PATH | 否 | SQLite 数据库路径，默认 `wechat_publisher.db` |

## 二、依赖安装

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 ffmpeg（macOS）

```bash
brew install ffmpeg
```

### 2. 安装 ffmpeg（Linux）

```bash
sudo apt install ffmpeg
```

### 2. 安装 ffmpeg（Windows）

使用 [ffmpeg官网](https://ffmpeg.org/download.html) 下载或：

```bash
winget install ffmpeg
```

## 三、启动应用

```bash
cd /Users/tyinzero/Desktop/claude/wechat_publisher
streamlit run app.py
```

启动后访问 `http://localhost:8501`

## 四、验证启动

运行后检查：

1. 页面标题显示"公众号自动发布工具"
2. 进度条显示 4 步：上传 / 转录 / 生成 / 发布确认
3. 无配置警告提示（若缺少环境变量会显示橙色警告框）

## 五、目录结构

```
wechat_publisher/
├── app.py              # Streamlit 主入口
├── config.py           # 配置文件
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量模板
├── core/               # 核心模块
│   ├── file_handler.py  # 文件处理
│   ├── transcriber.py   # 语音转录（Whisper）
│   ├── generator.py     # AI 文章生成（DeepSeek）
│   ├── publisher.py     # 微信公众号发布
│   └── database.py      # SQLite 数据库
├── uploads/            # 上传文件目录
├── outputs/            # 输出文件目录
└── data/               # 数据目录
```

## 六、常见问题

### Q: 启动时报 `ModuleNotFoundError`

执行：

```bash
pip install -r requirements.txt
```

### Q: 转录时报 `ffmpeg not found`

确保 ffmpeg 已安装并在 PATH 中：

```bash
ffmpeg -version
```

### Q: 提示配置缺失

检查 `.env` 文件是否创建且包含必要变量：

- DEEPSEEK_API_KEY
- WX_APP_ID
- WX_APP_SECRET
