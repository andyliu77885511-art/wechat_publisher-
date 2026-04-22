# 微信公众号 Cookie 模拟登录技术调研报告

## 一、调研目标

评估通过模拟 Cookie 登录 mp.weixin.qq.com 后台，实现文章发布的可行性，为改造 publisher.py 提供技术依据。

---

## 二、微信公众号登录认证体系

### 2.1 登录方式

微信公众号后台 (mp.weixin.qq.com) 支持两种登录方式：

| 登录方式 | 说明 |
|---------|------|
| 扫码登录 | 微信客户端扫码确认（推荐，更稳定） |
| 账号密码 | 邮箱/手机号 + 密码 + 验证码 |

两种方式最终都生成相同的 Session 体系，通过 Cookie 维护。

### 2.2 关键 Cookie 字段

登录 mp.weixin.qq.com 后，浏览器 Cookie 中包含以下关键字段：

```
┌─────────────────┬──────────────────────────────────────────────────────┐
│ Cookie 名称      │ 说明                                                  │
├─────────────────┼──────────────────────────────────────────────────────┤
│ pass_ticket     │ 核心认证票据，用于标识用户身份，跨请求传递                │
│ wxuin           │ 微信用户 ID，标识当前运营者身份                          │
│ data_bizuin     │ 当前登录的公众号 bizuin                                 │
│ token           │ API Token，部分接口需要                                │
│ masteruin       │ 主账号 UIN                                             │
│ session_id      │ 会话 ID                                               │
│ appmsgencrypt_* │ 消息加密相关票据                                       │
│ data_uin        │ 账号 UIN                                               │
└─────────────────┴──────────────────────────────────────────────────────┘
```

**最关键的三个字段**：
1. `pass_ticket` — 必须，每次请求几乎都要带
2. `wxuin` / `data_bizuin` — 标识当前操作哪个公众号
3. `token` — 部分接口需要从 Cookie 中提取

---

## 三、发布相关接口分析

### 3.1 接口列表

| 功能 | 接口 URL | 方法 | 关键参数 |
|------|----------|------|----------|
| 保存图文 | `mp.weixin.qq.com/cgi-bin/operate_appmsg` | POST | pass_ticket, token, appmsgid, content |
| 上传图片 | `mp.weixin.qq.com/cgi-bin/uploadimg` | POST | pass_ticket, token, file |
| 群发消息 | `mp.weixin.qq.com/cgi-bin/singlesend` | POST | pass_ticket, token, appmsgid, type |
| 登录验证 | `mp.weixin.qq.com/cgi-bin/login` | POST | username, password, imgcode |

### 3.2 草稿保存接口示例

```
POST /cgi-bin/operate_appmsg?token={TOKEN}&lang=zh_CN&f=json&ajax=1
Cookie: pass_ticket=xxx; wxuin=xxx; data_bizuin=xxx; token=xxx

t=appmsg_commit
&appmsgid={media_id}
&content={HTML内容}
&digest={摘要}
&ajax=1
```

### 3.3 群发接口示例

```
POST /cgi-bin/singlesend?t=ajax-response&lang=zh_CN
Cookie: pass_ticket=xxx; wxuin=xxx; data_bizuin=xxx

fid={appmsgid}
&appmsgid={media_id}
&operation=preview
& oauth_token ={oauth_token}
```

---

## 四、Cookie 模拟登录的技术可行性评估

### 4.1 结论：不可行 / 不推荐

**Cookie 模拟登录存在以下根本性障碍**：

#### (1) 登录流程复杂且不稳定

微信登录环节包含：
- 滑动验证码（极验/腾讯防水墙）
- 短信验证码（二次验证）
- 设备环境检测（User-Agent、屏幕分辨率、Canvas 指纹等）
- 频率限制（短时间多次登录会触发风控）

#### (2) appmsg_token 无法通过 Cookie 获取

群发接口需要 `appmsg_token`，这个 token 的生成依赖：
- 微信客户端环境
- 用户的登录态签名
- 一次性票据

通过 Cookie 无法正确生成，会导致群发失败。

#### (3) 反爬虫检测严格

微信后台有完善的风控体系：
- 请求频率限制
- IP 黑名单
- 行为模式检测
- 环境异常检测

自动化请求很容易被封禁。

#### (4) Cookie 有效期不可控

| Cookie 字段 | 预估有效期 | 说明 |
|-------------|-----------|------|
| pass_ticket | 1-7 天 | 视登录方式而定 |
| token | 2 小时 | 需要刷新 |
| session_id | 24 小时 | 可能更短 |
| wxuin | 数周 | 长期有效 |

登录态失效后无法自动恢复，必须重新走登录流程。

---

## 五、推荐方案：官方 API（已实现）+ 增强方案

### 5.1 现有方案评估

当前 publisher.py 使用的是**微信官方 API**：

```python
# 获取 access_token
GET https://api.weixin.qq.com/cgi-bin/token

# 创建草稿
POST https://api.weixin.qq.com/cgi-bin/draft/add

# 群发发布
POST https://api.weixin.qq.com/cgi-bin/freepublish/submit
```

**优势**：
- 官方接口，稳定性有保障
- 不需要处理登录、验证码
- token 自动管理
- 合规合法

**限制**：
- 需要公众号为已认证的服务号
- 群发次数受限（每月 4 次）
- 部分高级功能不可用

### 5.2 增强方案：半自动 Cookie + API 混合

如果确实需要更高级的发布能力，可以采用混合方案：

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ 浏览器自动化  │ -> │ 导出 Cookie  │ -> │ requests 调用   │
│ (Playwright) │    │ + appmsg_    │    │ 发布接口        │
│ 扫码登录     │    │ token        │    │ (fallback API)  │
└─────────────┘    └──────────────┘    └─────────────────┘
```

步骤：
1. 用 Playwright/Selenium 打开微信登录二维码
2. 用户扫码确认登录
3. 从浏览器上下文提取 Cookie + appmsg_token
4. 用提取的凭证调用发布接口
5. 凭证过期时自动触发重新登录

---

## 六、Cookie 失效检测方法

### 6.1 常见失效标识

```python
def is_cookie_expired(response_text: str) -> bool:
    """检测 Cookie 是否失效"""
    expired_signatures = [
        "错误的nonceStr",           # 签名错误
        "40001",                    # token 无效
        "42001",                    # token 过期
        "登录超时",                  # session 过期
        "请重新登录",                # 需要重新认证
        "redirect_uri",             # 重定向到登录页
    ]
    return any(sig in response_text for sig in expired_signatures)
```

### 6.2 主动检测接口

```python
def check_login_status(cookies: dict) -> bool:
    """检查登录态是否有效"""
    url = "https://mp.weixin.qq.com/cgi-bin/home"
    response = requests.get(url, cookies=cookies, allow_redirects=False)
    return response.status_code == 200 and "登录" not in response.url
```

---

## 七、最终建议

### 7.1 保留现有方案

当前 publisher.py 使用的官方 API 方案是**最优选择**：
- 稳定可靠
- 无需处理登录复杂性
- 维护成本低

### 7.2 如需升级，考虑 Hybrid 方案

如果 CEO 确认需要更高级的发布能力，建议：

```
Phase 1: 保留现有 API 模式（稳定）
Phase 2: 开发 Playwright 辅助登录模块（可选）
Phase 3: 按需切换到 Cookie 模式（高级用户）
```

### 7.3 publisher.py 改造建议

当前代码已经是基于官方 API 的实现，**无需大改**。如需增强：

1. 添加 Cookie 模式开关（config 中配置）
2. 实现 Playwright 辅助登录类
3. 添加双模式容错（Cookie 失败 fallback 到 API）

---

## 八、技术参数速查表

| 项目 | 值 |
|------|-----|
| 登录入口 | mp.weixin.qq.com |
| 核心 Cookie | pass_ticket, wxuin, data_bizuin, token |
| 草稿保存接口 | POST /cgi-bin/operate_appmsg (t=appmsg_commit) |
| 图片上传接口 | POST /cgi-bin/uploadimg |
| Cookie 有效期 | 1-7 天（视登录方式） |
| 稳定性评估 | Cookie 模式：不推荐；官方 API：推荐 |

---

*调研完成时间：2026-04-22*
*调研人：AK-CTO*
