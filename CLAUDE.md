# Hermes Desktop Pet

## 技术栈
- Python 3.10+ / PyQt5
- httpx (异步 HTTP + 流式响应)
- 运行环境：Windows 原生（非 WSL）

## API 接口
- Endpoint: `http://localhost:8642/v1/chat/completions`
- Auth: Bearer token（从环境变量 `HERMES_API_KEY` 读取，为空则不验证）
- Model: `hermes-agent`
- 格式：OpenAI Chat Completions 兼容，支持 stream=true

## 代码规范
- 中文注释
- 类型提示
- PyQt5 信号槽机制处理跨线程 UI 更新
- 所有 UI 文本中文

## 目录结构
```
hermes-desktop-pet/
├── main.py              # 入口
├── app/
│   ├── pet_window.py    # 桌面宠物窗口
│   ├── chat_bubble.py   # 聊天气泡
│   ├── api_client.py    # Hermes API 客户端
│   ├── tray_icon.py     # 系统托盘
│   └── config.py        # 配置
├── assets/              # 角色图片资源
└── requirements.txt
```

## 关键约束
- 角色用 QPainter 自绘（线条风格小女孩），不用外部图片依赖
- 透明无边框窗口，始终置顶
- 流式响应用 QThread + pyqtSignal 回调主线程
- 聊天历史保持在当前会话内存中
