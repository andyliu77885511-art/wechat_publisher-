# Streamlit Community Cloud 部署指南

## 概述

本项目将部署到 Streamlit Community Cloud（免费托管服务）。

**预期访问链接格式：** `https://wechat-publisher.streamlit.app`

---

## 第一步：登录 Streamlit Cloud

1. 打开浏览器访问：**https://share.streamlit.io**
2. 点击右上角 **"Sign in"**
3. 选择 **"Continue with GitHub"**（使用 GitHub 授权）
4. 如果弹出 GitHub 授权页面，点击 **"Authorize"** 确认授权

---

## 第二步：部署新应用

1. 登录成功后，点击右上角 **"New app"** 按钮

2. 填写部署配置：

   | 配置项 | 值 |
   |--------|-----|
   | Repository | `andyliu77885511-art/wechat_publisher-` |
   | Branch | `main` |
   | Main file path | `app.py` |

3. 点击 **"Deploy!"** 开始部署

---

## 第三步：配置环境变量（Secrets）

> 重要：公众号相关 API 需要配置才能正常使用

1. 部署完成后，进入 app 管理页面
2. 点击顶部 **"Settings"**（齿轮图标）
3. 选择左侧 **"Secrets"** 标签
4. 在文本框中粘贴以下内容（替换实际值）：

```toml
# OpenAI / Whisper
OPENAI_API_KEY = "sk-your-actual-openai-key"

# DeepSeek
DEEPSEEK_API_KEY = "sk-your-actual-deepseek-key"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 微信公众号（可选，如需发布功能）
WX_APP_ID = "wx_your_appid_here"
WX_APP_SECRET = "your_app_secret_here"

# 本地存储路径
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
DB_PATH = "wechat_publisher.db"
```

5. 点击 **"Save"** 保存

6. 应用会自动重启生效

---

## 第四步：验证部署

1. 等待 1-2 分钟让 Streamlit 构建并启动
2. 访问分配的域名，如：`https://wechat-publisher.streamlit.app`
3. 检查页面是否正常显示

---

## 常见问题

### Q: 部署失败怎么办？
A: 查看 Streamlit Cloud 的 deployment logs，常见问题：
- 缺少依赖 → 检查 requirements.txt
- 环境变量缺失 → 确认 Secrets 配置
- 代码错误 → 查看错误日志定位问题

### Q: 如何修改已部署的应用？
A: 推送代码到 GitHub main 分支后，Streamlit Cloud 会自动重新部署

### Q: 访问链接可以自定义吗？
A: 可以，在 Settings 里修改 Subdomain（但部分名称可能被占用）

---

## 部署检查清单

- [ ] GitHub 账号已登录 share.streamlit.io
- [ ] 仓库 `andyliu77885511-art/wechat_publisher-` 已授权
- [ ] 部署配置已填写（仓库/分支/主文件）
- [ ] Secrets 环境变量已配置
- [ ] 应用成功启动，可访问

---

## 环境变量说明

| 变量名 | 必填 | 说明 |
|--------|------|------|
| OPENAI_API_KEY | 是 | Whisper 转录需要 |
| DEEPSEEK_API_KEY | 是 | AI 生成文案需要 |
| DEEPSEEK_BASE_URL | 是 | DeepSeek API 地址 |
| WX_APP_ID | 否 | 微信公众号 AppID |
| WX_APP_SECRET | 否 | 微信公众号 AppSecret |
| UPLOAD_DIR | 否 | 上传文件存储目录 |
| OUTPUT_DIR | 否 | 输出文件存储目录 |
| DB_PATH | 否 | SQLite 数据库路径 |
