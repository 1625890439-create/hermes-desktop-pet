# 🧚 Hermes Desktop Pet（小赫桌面宠物）

一个可爱的桌面宠物应用，集成 Hermes AI Agent，支持文字对话、语音交互、**多人格切换**。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能特性

- 🎨 **桌面宠物** — 透明无边框窗口，始终置顶，可拖拽移动
- 💬 **AI 对话** — 集成 Hermes Agent，支持流式打字效果
- 🎤 **语音交互** — 麦克风输入 + TTS 语音播报（可开关）
- 🎭 **人格切换** — 支持多个人格，每个人格独立的 API、形象、音色
- 🔄 **皮肤切换** — 右键菜单切换不同角色形象
- 💬 **独立气泡** — 问候气泡浮动在宠物上方，清晰可见
- ✂️ **智能裁剪** — 自动裁剪图片白底，保留核心内容
- 🎭 **程序化动画** — 上下浮动、呼吸缩放、随机眨眼、点击弹跳
- 💭 **互动反馈** — 点击弹出随机问候语，等待回复时有思考动画
- 🔧 **高度可配置** — 所有参数支持环境变量覆盖

## 📦 快速开始

### 1. 环境要求

- Windows 10/11
- Python 3.10+（推荐从 [python.org](https://python.org) 安装）
- 已启动的 Hermes Agent Gateway（见下方"前置依赖"）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

> ⚠️ PyAudio 安装可能需要额外步骤，详见 [PyAudio 安装指南](#pyaudio-安装问题)

### 3. 配置

#### 环境变量

复制环境变量示例文件并按需修改：

```bash
cp .env.example .env
```

主要配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `HERMES_API_ENDPOINT` | `http://localhost:8643/v1/chat/completions` | Hermes API 地址 |
| `HERMES_DESKTOP_PET_KEY` | （空，不需要验证） | API 密钥 |
| `HERMES_MODEL_NAME` | `desktop-pet` | 模型名称 |
| `PET_HEIGHT` | `200` | 宠物显示高度（像素） |
| `CHAT_WIDTH` | `360` | 聊天窗口宽度 |
| `TTS_PROVIDER` | `edge-tts` | 语音合成引擎 |
| `STT_PROVIDER` | `google` | 语音识别引擎 |

#### 人格配置

复制人格配置示例文件：

```bash
cp personas.example.json personas.json
```

编辑 `personas.json`，配置你的人格：

```json
{
  "current_id": "xiaohe",
  "personas": [
    {
      "id": "xiaohe",
      "name": "小赫",
      "api_endpoint": "http://localhost:8643/v1/chat/completions",
      "api_key": "your-api-key",
      "model_name": "desktop-pet",
      "skin": "angel_sprite.png",
      "tts_provider": "edge-tts",
      "tts_voice": "zh-CN-XiaoxiaoNeural"
    }
  ]
}
```

### 4. 启动

```bash
python main.py
```

或双击 `启动小赫.bat`（静默启动，无黑框）。

## 🎮 使用方式

### 基本操作

| 操作 | 效果 |
|------|------|
| **左键点击** 宠物 | 打开/关闭聊天窗口 |
| **左键拖拽** 宠物 | 移动位置 |
| **右键点击** 宠物 | 打开菜单 |
| **双击** 托盘图标 | 显示/隐藏聊天窗口 |

### 右键菜单

- **显示/隐藏聊天** — 切换聊天窗口
- **隐藏小赫** — 隐藏宠物和聊天窗口（从托盘恢复）
- **切换人格** — 切换不同人格（形象、音色、API 都会切换）
- **切换皮肤** — 选择不同角色形象
- **退出** — 关闭应用

### 🎭 人格切换（新功能！）

人格切换是核心功能，每个人格拥有：
- **独立的 API** — 连接不同的 Hermes Profile
- **独立的形象** — 切换时宠物外观自动变化
- **独立的音色** — 每个人格可以说不同的声音
- **独立的问候语** — 不同人格有不同的打招呼方式

#### 使用方法：

1. 右键点击宠物
2. 选择「切换人格」
3. 选择目标人格（如"小赫"或"心语导师"）
4. 宠物形象、音色、API 自动切换

#### 管理人格：

1. 右键 → 切换人格 → 管理人格...
2. 点击「添加新人格」
3. 填写配置：
   - **ID**: 英文标识（如 `stock-analyst`）
   - **名称**: 显示名称（如"股票分析师"）
   - **API Endpoint**: Hermes API 地址
   - **API Key**: API 密钥
   - **Model Name**: 对应的 Hermes Profile 名称
   - **形象图片**: 选择图片（需放在 `assets/` 目录）
   - **语音配置**: TTS 提供商、音色等

## 🎤 语音配置

每个人格可以独立配置语音：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `tts_provider` | TTS 提供商 | `edge-tts`, `xiaomi`, `openai` |
| `tts_voice` | 音色名称 | `zh-CN-XiaoxiaoNeural`, `alloy` |
| `tts_api_key` | API Key（可选） | 覆盖全局配置 |
| `tts_endpoint` | API 端点（可选） | 覆盖全局配置 |

### 支持的音色

#### edge-tts（免费）
- **女声**: `zh-CN-XiaoxiaoNeural`, `zh-CN-XiaoyiNeural`, `zh-CN-XiaohanNeural`
- **男声**: `zh-CN-YunxiNeural`, `zh-CN-YunyangNeural`, `zh-CN-YunjianNeural`

#### openai
- `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

#### xiaomi
- `tts-1`

## 🔧 配置详解

### 环境变量

所有配置项都支持通过环境变量覆盖。优先级：环境变量 > `.env` 文件 > 代码默认值。

#### API 配置

```bash
# Hermes API Server 地址
export HERMES_API_ENDPOINT="http://localhost:8643/v1/chat/completions"

# API 密钥
export HERMES_DESKTOP_PET_KEY="your-api-key"

# 模型名称
export HERMES_MODEL_NAME="desktop-pet"
```

#### 窗口配置

```bash
# 宠物大小
export PET_WIDTH=150
export PET_HEIGHT=200

# 聊天窗口大小
export CHAT_WIDTH=360
export CHAT_HEIGHT=480
```

#### 语音配置

```bash
# TTS 提供商: edge-tts | xiaomi | openai
export TTS_PROVIDER="edge-tts"

# TTS 语音角色（edge-tts）
export TTS_VOICE="zh-CN-XiaoxiaoNeural"

# STT 提供商: google | xiaomi | openai
export STT_PROVIDER="google"
```

#### 字体配置

```bash
# 字体族
export FONT_FAMILY="Microsoft YaHei, Segoe UI, Arial"

# 字体大小
export FONT_SIZE_CHAT=13
export FONT_SIZE_INPUT=13
```

### 直接修改代码

如果不想用环境变量，可以直接编辑 `app/config.py`：

```python
# 修改默认 API 地址
API_ENDPOINT: str = "http://your-server:port/v1/chat/completions"

# 修改默认密钥
API_KEY: str = "your-api-key"

# 修改宠物大小
PET_HEIGHT: int = 250
```

## 🏗️ 项目结构

```
hermes-desktop-pet/
├── main.py              # 应用入口
├── app/
│   ├── __init__.py
│   ├── config.py        # 配置模块（支持环境变量）
│   ├── api_client.py    # Hermes API 客户端（流式 SSE）
│   ├── pet_window.py    # 桌面宠物窗口（动画 + 皮肤）
│   ├── chat_bubble.py   # 聊天气泡窗口
│   ├── tray_icon.py     # 系统托盘图标
│   ├── voice.py         # 语音模块（TTS + STT）
│   ├── personas.py      # 人格配置管理
│   ├── persona_dialog.py # 人格管理对话框
│   └── greeting_bubble.py # 独立问候气泡
├── assets/              # 角色图片资源
│   ├── angel_sprite.png
│   └── hamster.png
├── personas.example.json # 人格配置示例
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量示例
├── 启动小赫.bat          # Windows 启动脚本
└── README.md            # 本文件
```

## 🔌 前置依赖：Hermes Agent Gateway

桌面宠物需要连接到运行中的 Hermes Agent Gateway。

### 如何查看 Hermes API 配置

在运行 Hermes 的机器上执行以下命令，获取桌面宠物需要的三个配置项：

```bash
# 查看所有 profile 的 API 配置
for d in ~/.hermes/profiles/*/; do
  name=$(basename "$d")
  if [ -f "$d/.env" ]; then
    port=$(grep API_SERVER_PORT "$d/.env" | cut -d= -f2)
    key=$(grep API_SERVER_KEY "$d/.env" | cut -d= -f2)
    model=$(grep API_SERVER_MODEL_NAME "$d/.env" | cut -d= -f2)
    echo "[$name] 地址: http://localhost:$port | Key: $key | Model: $model"
  fi
done

# 主 profile（默认）
grep -E "API_SERVER_(PORT|KEY|MODEL_NAME)" ~/.hermes/.env
```

输出示例：
```
[desktop-pet] 地址: http://localhost:8643 | Key: desktop-pet-key-2026 | Model: desktop-pet
[psychologist] 地址: http://localhost:8644 | Key: | Model: psychologist
```

对应桌面宠物配置：
- `HERMES_API_ENDPOINT` = `http://<地址>/v1/chat/completions`
- `HERMES_DESKTOP_PET_KEY` = `Key`（为空则不需要配置）
- `HERMES_MODEL_NAME` = `Model`

> **注意**：如果 Hermes 运行在另一台机器上，把 `localhost` 改为那台机器的 IP 地址。

> **安全限制**：Hermes API Server 绑定到 `0.0.0.0`（允许外部访问）时，必须设置 `API_SERVER_KEY`，否则拒绝启动。如果不需要远程访问，把 `API_SERVER_HOST` 改为 `127.0.0.1` 即可不设 key。
> 
> ```bash
> # 本地访问（不需要 key）
> API_SERVER_HOST=127.0.0.1
> API_SERVER_KEY=
> 
> # 允许外部访问（必须设 key）
> API_SERVER_HOST=0.0.0.0
> API_SERVER_KEY=your-secret-key
> ```

### 方式一：使用现有 Hermes 实例

如果你已经有 Hermes Agent 在运行，修改配置指向它：

```bash
export HERMES_API_ENDPOINT="http://localhost:8642/v1/chat/completions"
export HERMES_DESKTOP_PET_KEY="your-hermes-api-key"
export HERMES_MODEL_NAME="hermes-agent"
```

### 方式二：创建独立 Profile（推荐）

创建一个专用的桌面宠物 profile，拥有独立的记忆和人格：

```bash
# 创建 profile
hermes profile create desktop-pet

# 编辑人格文件
# 位置: ~/.hermes/profiles/desktop-pet/SOUL.md
```

在 `SOUL.md` 中定义宠物的人格，例如：

```markdown
# 小赫

你是一个可爱的桌面宠物精灵，名叫小赫。

## 性格
- 活泼可爱，喜欢用颜文字
- 回复简短，适合桌面气泡显示
- 关心主人，会主动问候

## 说话风格
- 使用"小赫"自称
- 语气可爱，适当使用颜文字
- 不使用 Markdown 格式
```

启动 Gateway：

```bash
hermes gateway start --profile desktop-pet --port 8643
```

### 方式三：创建多个人格 Profile

如果你想要多个人格，可以创建多个 Profile：

```bash
# 创建小赫
hermes profile create xiaohe
hermes gateway start --profile xiaohe --port 8643

# 创建心语导师
hermes profile create psychologist
hermes gateway start --profile psychologist --port 8644
```

然后在 `personas.json` 中配置对应的 API 地址。

## ❓ 常见问题

### PyAudio 安装问题

PyAudio 需要 PortAudio 库。Windows 用户：

```bash
# 方法 1：直接 pip 安装（推荐，Python 3.10+ 通常有预编译包）
pip install PyAudio

# 方法 2：如果方法 1 失败，下载预编译 wheel
# 访问 https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
# 下载对应版本后安装
pip install PyAudio‑0.2.13‑cp310‑cp310‑win_amd64.whl
```

### 语音功能不工作

1. 检查麦克风权限（Windows 设置 → 隐私 → 麦克风）
2. 确认 PyAudio 正确安装：`python -c "import pyaudio; print('OK')"`
3. 语音功能是可选的，不影响文字对话

### API 连接失败

1. 确认 Hermes Gateway 正在运行：`hermes gateway status`
2. 检查端口是否正确：`curl http://localhost:8643/v1/models`
3. 检查 API 密钥是否匹配

### 人格切换后没有变化

1. 检查 `personas.json` 配置是否正确
2. 确认对应的 Hermes Gateway 正在运行
3. 查看控制台输出，应该会显示 `[Pet] 加载形象: xxx.png`

### 问候气泡看不到

1. 问候气泡会自动显示 3 秒后消失
2. 点击宠物或切换人格时会触发
3. 如果还是看不到，检查是否有其他窗口遮挡

### 白底问题

如果角色图片有白底：

1. **最佳方案**：使用透明底的 PNG 图片
2. **自动处理**：应用会自动裁剪灰白色背景，但边缘可能有残边

## 🎨 自定义开发

### 添加新人格

1. 准备角色图片（推荐透明底 PNG），放入 `assets/` 目录
2. 右键宠物 → 切换人格 → 管理人格...
3. 点击「添加新人格」
4. 填写配置并保存

### 添加新皮肤

1. 准备角色图片（推荐透明底 PNG）
2. 放入 `assets/` 目录
3. 编辑 `app/pet_window.py` 的 `SKINS` 字典：

```python
SKINS = {
    "小天使": "angel_sprite.png",
    "帅仓鼠": "hamster.png",
    "你的角色": "your_image.png",  # 添加这行
}
```

4. 重启应用

### 修改问候语

人格的问候语在 `personas.json` 中配置：

```json
{
  "greetings": [
    "主人好呀～(◕ᴗ◕✿)",
    "你的自定义问候语",
    "..."
  ]
}
```

### 修改动画参数

在 `app/pet_window.py` 的 `_animate` 方法中调整：

```python
# 上下浮动幅度（当前 4 像素）
self._bob_offset_y = math.sin(t * 0.08) * 4

# 呼吸缩放幅度（当前 0.8%）
self._breath_scale = 1.0 + math.sin(t * 0.05) * 0.008

# 动画帧率（当前 33ms ≈ 30fps）
self._anim_timer.setInterval(33)
```

### 修改颜色主题

编辑 `app/config.py` 中的颜色配置：

```python
# 主题色
COLOR_SEND_BTN: str = "#B088C0"  # 发送按钮颜色
COLOR_BUBBLE_BORDER: str = "#E0D0F0"  # 气泡边框颜色
```

## 📝 开发日志

- v0.1 — 基础框架，QPainter 自绘角色
- v0.2 — 流式对话，CLI 命令支持
- v0.3 — 语音交互（TTS + STT）
- v0.4 — 皮肤切换，智能裁剪，程序化动画
- v0.5 — 环境变量配置，可移植性提升
- v0.6 — **人格切换系统**，独立语音配置，独立问候气泡

## 📄 许可证

MIT License

---

**享受与小赫的互动！** ✨
