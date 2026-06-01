# Hermes Desktop Pet — 桌面宠物聊天应用

## 项目概述
一个 Windows 桌面宠物应用，以 Hermes 线条小女孩形象呈现，用户可以直接在桌面上与 Hermes AI 进行文字对话和下达指令。

## 技术架构

```
┌─────────────────────────────────────┐
│         Desktop Pet (PyQt5)         │
│  ┌──────────┐  ┌─────────────────┐  │
│  │ 角色动画  │  │   聊天气泡 UI    │  │
│  │ (SVG/PNG)│  │  (对话+输入框)   │  │
│  └──────────┘  └─────────────────┘  │
│         │                           │
│  ┌──────────────────────────────┐   │
│  │   Hermes API Client          │   │
│  │   (OpenAI-compatible HTTP)   │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
              │ HTTP POST
              ▼
   ┌─────────────────────┐
   │  Hermes API Server   │
   │  localhost:8642      │
   │  /v1/chat/completions│
   └─────────────────────┘
```

## API 接口
- **Endpoint**: `http://localhost:8642/v1/chat/completions`
- **Auth**: Bearer token `hermes-webui-key-2026`
- **Model**: `hermes-agent`
- **Format**: OpenAI Chat Completions 兼容

### 请求示例
```json
POST /v1/chat/completions
Authorization: Bearer hermes-webui-key-2026
Content-Type: application/json

{
  "model": "hermes-agent",
  "messages": [
    {"role": "system", "content": "You are Hermes, a helpful desktop assistant."},
    {"role": "user", "content": "你好"}
  ],
  "stream": true
}
```

## 功能需求

### P0（MVP 必须）
1. **桌面宠物形象**：线条风格小女孩，显示在桌面右下角
   - 无边框透明窗口，始终置顶
   - 可拖拽移动位置
   - 右键菜单：退出、设置、最小化
   
2. **聊天功能**：
   - 点击角色弹出聊天气泡/对话框
   - 支持文字输入和发送
   - 支持流式输出（打字机效果）
   - 对话历史保持（当前会话内）
   
3. **指令下达**：
   - 用户可以输入自然语言指令（如"帮我查一下天气"、"总结这段文字"）
   - Hermes 的回复在气泡中显示

### P1（增强）
4. **系统托盘**：最小化到系统托盘，双击恢复
5. **消息通知**：Hermes 回复时有轻微动画/提示
6. **快捷键**：全局快捷键呼出/隐藏对话框

### P2（后续迭代）
7. **语音交互**：麦克风输入 + TTS 语音播报
8. **角色动画**：待机、说话、思考等不同状态动画
9. **主题皮肤**：支持切换不同角色风格

## 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| GUI 框架 | PyQt5 | 透明窗口、系统托盘、原生感强 |
| HTTP 客户端 | httpx | 支持异步 + 流式响应 |
| 角色资源 | SVG 矢量图 | 缩放不失真 |
| 打包 | PyInstaller | 打包成 Windows exe |

## 项目结构
```
hermes-desktop-pet/
├── PLAN.md                 # 本文件
├── requirements.txt        # Python 依赖
├── main.py                 # 入口
├── app/
│   ├── __init__.py
│   ├── pet_window.py       # 桌面宠物主窗口（角色显示、拖拽）
│   ├── chat_bubble.py      # 聊天气泡组件
│   ├── api_client.py       # Hermes API 客户端（流式通信）
│   ├── tray_icon.py        # 系统托盘
│   └── config.py           # 配置（API 地址、密钥等）
├── assets/
│   ├── hermes_girl.svg     # 线条小女孩主图
│   ├── hermes_girl_idle.png # 待机状态
│   ├── hermes_girl_talk.png # 说话状态
│   ├── hermes_girl_think.png # 思考状态
│   └── tray_icon.ico       # 托盘图标
└── README.md
```

## UI 设计要点
- 角色大小：约 120x160px
- 聊天气泡：出现在角色旁边，宽度 320px，高度自适应
- 配色：柔和温暖，与 Hermes 品牌一致
- 字体：微软雅黑 / Segoe UI
- 圆角对话框，半透明背景

## 开发约束
- **Python 3.10+** 兼容
- **Windows 原生运行**（不是 WSL）
- API 密钥不要硬编码，优先从环境变量 `HERMES_API_KEY` 读取，fallback 到配置文件
- 所有 UI 文本使用中文
- 流式响应回调要在主线程更新 UI（避免 PyQt 线程问题）

## 验收标准
1. ✅ 双击 `main.py` 或 exe 启动，桌面出现线条小女孩
2. ✅ 点击角色弹出聊天框，输入文字可发送
3. ✅ Hermes 回复实时流式显示
4. ✅ 可以拖拽移动角色位置
5. ✅ 右键菜单可退出
6. ✅ 系统托盘图标正常显示
