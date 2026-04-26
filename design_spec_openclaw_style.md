# wechat_publisher UI 改版设计方案（openclaw.ai 风格）

## 一、openclaw.ai 设计特征提取

### 1. 配色方案
- **主背景**：深蓝黑渐变（#0a1628 → #1a2332 → #0d1b2a），专业克制
- **强调色**：橙色系（#FF8C00 / #FFA500），用于 CTA 按钮、hover 状态、重点标记
- **文字色**：
  - 主标题：纯白 #ffffff
  - 副标题/说明：rgba(255,255,255,0.6)
  - 次要文字：rgba(255,255,255,0.4)
- **卡片背景**：半透明白色叠加（rgba(255,255,255,0.03) ~ 0.06），带 backdrop-filter: blur(10px)
- **边框**：rgba(255,255,255,0.08) ~ 0.12，细线风格

### 2. 字体与排版
- **标题字重**：700-800（Bold/ExtraBold）
- **正文字重**：400-500（Regular/Medium）
- **字号层级**：
  - H1: 2.2rem
  - H2: 1.5rem
  - Body: 0.9-1rem
  - Caption: 0.85rem
- **行高**：1.6-1.8，留白充足
- **字间距**：标题 -0.5px ~ -0.8px，紧凑现代感

### 3. 卡片与容器
- **圆角**：12-16px，柔和不失专业
- **内边距**：1.5-2rem，宽松舒适
- **阴影**：极少使用，主要靠边框和半透明背景区分层次
- **hover 效果**：
  - 边框颜色变为橙色系（rgba(255,165,0,0.3)）
  - 轻微阴影增强（0 4px 20px rgba(255,165,0,0.08)）
  - 过渡时间 0.3s ease

### 4. 交互元素
- **按钮**：
  - 主按钮：橙色渐变背景（#FF8C00 → #FFA500），白色文字，圆角 10-12px
  - 次按钮：半透明白色背景（rgba(255,255,255,0.08)），白色文字
  - hover：轻微上浮（translateY(-2px)）+ 阴影增强
- **输入框**：
  - 背景：rgba(255,255,255,0.05)
  - 边框：rgba(255,255,255,0.1)
  - focus：边框变橙色，底部加 2px 橙色下划线
- **选择器**：
  - 与输入框风格一致
  - 下拉菜单背景：深色半透明 + 毛玻璃效果

### 5. 整体调性
- **专业克制**：深色背景 + 低饱和度配色，避免花哨
- **现代简洁**：大圆角、细边框、充足留白
- **橙色点缀**：橙色作为唯一强调色，用于 CTA 和 hover 状态，形成视觉焦点
- **毛玻璃质感**：backdrop-filter: blur(10px) 营造层次感

---

## 二、wechat_publisher 改版方案

### 1. 全局背景
```css
background: linear-gradient(135deg, #0a1628 0%, #1a2332 50%, #0d1b2a 100%);
```

### 2. 公众号定位选择器（重点改版区域）

#### 当前问题
- 选择器与整体风格不协调
- 视觉层次不清晰
- 缺少 hover 反馈

#### 改版方案
```css
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
}
```

### 3. 按钮系统
- **主按钮（开始处理、确认发布）**：橙色渐变 + hover 上浮
- **次按钮（返回、上一步）**：半透明白色 + hover 变亮
- **下载按钮**：绿色系（保持原有区分）

### 4. 输入框与文本域
- 背景：rgba(255,255,255,0.06)
- 边框：rgba(255,255,255,0.1)
- focus：橙色边框 + 底部 2px 橙色下划线

### 5. 步骤指示器
- 保持原有圆点风格
- 激活状态改为橙色（#FFA500）
- 完成状态改为绿色（#43E97B）

### 6. 提示框
- warning：橙色系（rgba(255,140,0,0.15) 背景 + 橙色边框）
- success：绿色系（保持原有）
- error：红色系（保持原有）

---

## 三、实施要点

1. **CSS 注入方式**：st.markdown + unsafe_allow_html=True
2. **Streamlit 组件覆盖**：
   - .stButton > button
   - .stTextInput > div > div > input
   - .stTextArea > div > div > textarea
   - .stSelectbox > div > div > select
3. **响应式适配**：max-width: 820px，居中布局
4. **动画效果**：
   - fadeInDown（标题）
   - slideInUp（卡片）
   - hover 过渡 0.3s ease

---

## 四、预估工期

设计方案输出 + CSS 实现 + 本地测试 + GitHub 推送：2 小时
