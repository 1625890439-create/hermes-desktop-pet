"""主题系统模块 — 管理 UI 主题配置与切换

提供 Theme 数据类、ThemeManager 单例、4 套预设主题，
支持从 themes.json 持久化加载/保存。

用法:
    from app.theme import theme_manager
    theme = theme_manager.get_current()
    theme.border_radius  # 12
    theme_manager.switch_theme("cyber")
"""

import json
import os
import logging
from typing import Optional
from dataclasses import dataclass, field, asdict

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

# 配置文件路径
_CONFIG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES_FILE = os.path.join(_CONFIG_DIR, "themes.json")


# ═══════════════════════════════════════════════════════════════
# Theme 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass
class Theme:
    """UI 主题配置，所有属性均用于样式渲染。"""

    # 标识
    id: str = "glass"
    name: str = "毛玻璃"

    # ── 窗口层级 ──
    background_color: str = "rgba(255, 255, 255, 230)"
    background_opacity: float = 0.95        # setWindowOpacity 值（glass 主题用）
    bubble_bg: str = "rgba(255, 255, 255, 230)"
    bubble_border: str = "#E0D0F0"

    # ── 圆角 & 间距 ──
    border_radius: int = 12                 # 基础圆角
    bubble_border_radius: int = 16          # 气泡窗口圆角
    padding_v: int = 8
    padding_h: int = 12
    spacing: int = 6

    # ── 文字颜色 ──
    text_color: str = "#2D2D2D"
    text_secondary: str = "#666666"

    # ── 输入区域 ──
    input_bg: str = "#FFFFFF"
    input_border: str = "#D0C0E0"
    input_focus_border: str = "#B088C0"

    # ── 按钮 ──
    send_btn_bg: str = "#B088C0"
    send_btn_text: str = "#FFFFFF"
    send_btn_hover: str = "#9868A8"
    send_btn_pressed: str = "#805090"

    # ── 消息气泡 ──
    user_msg_bg: str = "#E8DEF8"
    hermes_msg_bg: str = "#F0E6FF"
    error_bg: str = "#FFF0F0"
    error_text: str = "#CC4444"
    error_border: str = "#FFD0D0"

    # ── 附件按钮（语音、麦克风） ──
    mic_btn_bg: str = "#F0E6FF"
    mic_btn_border: str = "#D0C0E0"
    mic_btn_hover: str = "#E0D0F5"
    mic_btn_pressed: str = "#D0C0E8"

    voice_btn_bg: str = "#E8F5E9"
    voice_btn_border: str = "#C8E6C9"
    voice_btn_checked_bg: str = "#C8E6C9"
    voice_btn_checked_border: str = "#A5D6A7"
    voice_btn_hover: str = "#DCEDC8"

    # ── 标题栏 ──
    title_color: str = "#2D2D2D"
    titlebar_btn_color: str = "#999999"
    titlebar_btn_hover_bg: str = "#E8DEF8"
    titlebar_btn_hover_text: str = "#666666"
    close_btn_hover_bg: str = "#FF6B6B"
    close_btn_hover_text: str = "#FFFFFF"

    # ── 右键菜单 ──
    menu_bg: str = "#FFFFFF"
    menu_border: str = "#D0C0E0"
    menu_border_radius: int = 6
    menu_item_padding: str = "6px 20px"
    menu_item_hover_bg: str = "#E8DEF8"
    menu_font_size: int = 12

    # ── 分隔线 ──
    separator_color: str = "#B088C0"

    # ── 滚动条 ──
    scrollbar_width: int = 6
    scrollbar_handle: str = "#C0B0D0"
    scrollbar_handle_radius: int = 3

    # ── 选区高亮 ──
    selection_bg: str = "#C8A8E8"

    # ── 阴影 ──
    shadow_enabled: bool = False
    shadow_color: str = "rgba(0, 0, 0, 30)"
    shadow_blur: float = 15.0
    shadow_offset_x: float = 0.0
    shadow_offset_y: float = 2.0

    # ── 毛玻璃效果 ──
    glass_effect: bool = False              # 是否启用半透明毛玻璃风格

    # ── 托盘图标 ──
    tray_icon_bg: str = "#B088C0"
    tray_icon_text_color: str = "#FFFFFF"

    # 额外的自定义 CSS 片段（运行时注入到特定组件）
    extra_css: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# 预设主题定义
# ═══════════════════════════════════════════════════════════════

PRESET_THEMES: dict[str, Theme] = {
    # ── 毛玻璃半透明风 ──
    "glass": Theme(
        id="glass",
        name="毛玻璃",
        background_color="rgba(255, 255, 255, 200)",
        background_opacity=0.95,
        bubble_bg="rgba(255, 255, 255, 210)",
        bubble_border="rgba(200, 180, 220, 120)",
        border_radius=14,
        bubble_border_radius=18,
        padding_v=10,
        padding_h=14,
        text_color="#2D2D2D",
        text_secondary="#888888",
        input_bg="rgba(255, 255, 255, 180)",
        input_border="rgba(200, 180, 220, 100)",
        input_focus_border="#B088C0",
        send_btn_bg="rgba(176, 136, 192, 200)",
        send_btn_text="#FFFFFF",
        send_btn_hover="rgba(152, 104, 168, 220)",
        send_btn_pressed="rgba(128, 80, 144, 240)",
        user_msg_bg="rgba(232, 222, 248, 180)",
        hermes_msg_bg="rgba(240, 230, 255, 180)",
        error_bg="rgba(255, 240, 240, 200)",
        error_text="#CC4444",
        error_border="rgba(255, 208, 208, 150)",
        mic_btn_bg="rgba(240, 230, 255, 180)",
        mic_btn_border="rgba(208, 192, 224, 120)",
        mic_btn_hover="rgba(224, 208, 245, 200)",
        mic_btn_pressed="rgba(208, 192, 232, 220)",
        voice_btn_bg="rgba(232, 245, 233, 180)",
        voice_btn_border="rgba(200, 230, 201, 120)",
        voice_btn_checked_bg="rgba(200, 230, 201, 200)",
        voice_btn_checked_border="rgba(165, 214, 167, 180)",
        voice_btn_hover="rgba(220, 236, 200, 200)",
        title_color="#2D2D2D",
        titlebar_btn_color="#AAAAAA",
        titlebar_btn_hover_bg="rgba(232, 222, 248, 120)",
        titlebar_btn_hover_text="#666666",
        close_btn_hover_bg="rgba(255, 107, 107, 200)",
        close_btn_hover_text="#FFFFFF",
        menu_bg="rgba(255, 255, 255, 240)",
        menu_border="rgba(208, 192, 224, 100)",
        menu_border_radius=8,
        menu_item_hover_bg="rgba(232, 222, 248, 100)",
        separator_color="rgba(176, 136, 192, 80)",
        scrollbar_handle="rgba(192, 176, 208, 120)",
        selection_bg="rgba(200, 168, 232, 150)",
        shadow_enabled=True,
        shadow_color="rgba(0, 0, 0, 20)",
        shadow_blur=20.0,
        shadow_offset_x=0.0,
        shadow_offset_y=4.0,
        glass_effect=True,
        tray_icon_bg="rgba(176, 136, 192, 200)",
    ),
    # ── 暗色科技风 ──
    "cyber": Theme(
        id="cyber",
        name="暗色科技",
        background_color="#1E1E2E",
        background_opacity=1.0,
        bubble_bg="#1E1E2E",
        bubble_border="#00D4FF",
        border_radius=8,
        bubble_border_radius=12,
        padding_v=8,
        padding_h=12,
        text_color="#CDD6F4",
        text_secondary="#6C7086",
        input_bg="#181825",
        input_border="#313244",
        input_focus_border="#00D4FF",
        send_btn_bg="#00D4FF",
        send_btn_text="#1E1E2E",
        send_btn_hover="#00B8E6",
        send_btn_pressed="#0099CC",
        user_msg_bg="#313244",
        hermes_msg_bg="#252536",
        error_bg="#3E1E2E",
        error_text="#FF6B8A",
        error_border="#6B3040",
        mic_btn_bg="#252536",
        mic_btn_border="#45475A",
        mic_btn_hover="#313244",
        mic_btn_pressed="#1E1E2E",
        voice_btn_bg="#1E2E24",
        voice_btn_border="#2E4E36",
        voice_btn_checked_bg="#2E4E36",
        voice_btn_checked_border="#3E6E4A",
        voice_btn_hover="#2A3A30",
        title_color="#CDD6F4",
        titlebar_btn_color="#6C7086",
        titlebar_btn_hover_bg="#313244",
        titlebar_btn_hover_text="#CDD6F4",
        close_btn_hover_bg="#FF6B8A",
        close_btn_hover_text="#1E1E2E",
        menu_bg="#1E1E2E",
        menu_border="#45475A",
        menu_border_radius=4,
        menu_item_hover_bg="#313244",
        separator_color="#00D4FF",
        scrollbar_handle="#45475A",
        scrollbar_handle_radius=4,
        selection_bg="#00D4FF44",
        shadow_enabled=True,
        shadow_color="rgba(0, 212, 255, 40)",
        shadow_blur=12.0,
        shadow_offset_x=0.0,
        shadow_offset_y=0.0,
        glass_effect=False,
        tray_icon_bg="#00D4FF",
    ),
    # ── 可爱卡通风 ──
    "cute": Theme(
        id="cute",
        name="可爱卡通",
        background_color="#FFF8F8",
        background_opacity=1.0,
        bubble_bg="#FFF8F8",
        bubble_border="#FFB6C1",
        border_radius=16,
        bubble_border_radius=20,
        padding_v=10,
        padding_h=14,
        text_color="#4A2D3E",
        text_secondary="#8B6B7A",
        input_bg="#FFFFFF",
        input_border="#FFD0DC",
        input_focus_border="#FF8C94",
        send_btn_bg="#FF8C94",
        send_btn_text="#FFFFFF",
        send_btn_hover="#FF6B7A",
        send_btn_pressed="#E5556A",
        user_msg_bg="#FFE4E8",
        hermes_msg_bg="#FFF0F4",
        error_bg="#FFF0F0",
        error_text="#E5556A",
        error_border="#FFD0DC",
        mic_btn_bg="#FFF0F4",
        mic_btn_border="#FFD0DC",
        mic_btn_hover="#FFE4E8",
        mic_btn_pressed="#FFD0DC",
        voice_btn_bg="#F0FFF4",
        voice_btn_border="#C8FFD4",
        voice_btn_checked_bg="#C8FFD4",
        voice_btn_checked_border="#A8FFB8",
        voice_btn_hover="#DCFFE4",
        title_color="#4A2D3E",
        titlebar_btn_color="#B0889A",
        titlebar_btn_hover_bg="#FFE4E8",
        titlebar_btn_hover_text="#4A2D3E",
        close_btn_hover_bg="#FF8C94",
        close_btn_hover_text="#FFFFFF",
        menu_bg="#FFFFFF",
        menu_border="#FFD0DC",
        menu_border_radius=12,
        menu_item_hover_bg="#FFE4E8",
        separator_color="#FFB6C1",
        scrollbar_handle="#FFD0DC",
        scrollbar_handle_radius=6,
        selection_bg="#FFB6C1",
        shadow_enabled=True,
        shadow_color="rgba(255, 140, 148, 25)",
        shadow_blur=16.0,
        shadow_offset_x=0.0,
        shadow_offset_y=3.0,
        glass_effect=False,
        tray_icon_bg="#FF8C94",
    ),
    # ── 简约扁平风 ──
    "minimal": Theme(
        id="minimal",
        name="简约扁平",
        background_color="#FFFFFF",
        background_opacity=1.0,
        bubble_bg="#FFFFFF",
        bubble_border="#E0E0E0",
        border_radius=4,
        bubble_border_radius=8,
        padding_v=6,
        padding_h=10,
        text_color="#212121",
        text_secondary="#757575",
        input_bg="#FAFAFA",
        input_border="#E0E0E0",
        input_focus_border="#424242",
        send_btn_bg="#424242",
        send_btn_text="#FFFFFF",
        send_btn_hover="#212121",
        send_btn_pressed="#000000",
        user_msg_bg="#F5F5F5",
        hermes_msg_bg="#FAFAFA",
        error_bg="#FFF5F5",
        error_text="#D32F2F",
        error_border="#FFCDD2",
        mic_btn_bg="#FAFAFA",
        mic_btn_border="#E0E0E0",
        mic_btn_hover="#F5F5F5",
        mic_btn_pressed="#EEEEEE",
        voice_btn_bg="#FAFAFA",
        voice_btn_border="#E0E0E0",
        voice_btn_checked_bg="#E8F5E9",
        voice_btn_checked_border="#C8E6C9",
        voice_btn_hover="#F5F5F5",
        title_color="#212121",
        titlebar_btn_color="#9E9E9E",
        titlebar_btn_hover_bg="#EEEEEE",
        titlebar_btn_hover_text="#424242",
        close_btn_hover_bg="#F44336",
        close_btn_hover_text="#FFFFFF",
        menu_bg="#FFFFFF",
        menu_border="#E0E0E0",
        menu_border_radius=2,
        menu_item_hover_bg="#F5F5F5",
        separator_color="#E0E0E0",
        scrollbar_handle="#BDBDBD",
        scrollbar_handle_radius=2,
        selection_bg="#BBDEFB",
        shadow_enabled=False,
        glass_effect=False,
        tray_icon_bg="#424242",
    ),
}


# ═══════════════════════════════════════════════════════════════
# ThemeManager 单例
# ═══════════════════════════════════════════════════════════════

class ThemeManager(QObject):
    """主题管理器单例，管理主题加载、保存与切换。

    用法:
        manager = ThemeManager()
        current = manager.get_current()
        manager.switch_theme("cyber")

    信号:
        theme_changed(theme_id: str) — 主题切换时发出
    """

    theme_changed = pyqtSignal(str)  # 新主题 ID

    _instance: Optional["ThemeManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ThemeManager._initialized:
            return
        super().__init__()
        ThemeManager._initialized = True

        self._current_id: str = "glass"
        self._custom_themes: dict[str, Theme] = {}

        # 合并预设到可用主题池
        self._available: dict[str, Theme] = dict(PRESET_THEMES)

        self._load()

    # ── 属性 ──

    @property
    def current_id(self) -> str:
        return self._current_id

    @property
    def current_name(self) -> str:
        theme = self.get_current()
        return theme.name if theme else "未知"

    # ── 获取 ──

    def get_current(self) -> Optional[Theme]:
        """获取当前激活的主题。"""
        return self._available.get(self._current_id)

    def get_all(self) -> list[Theme]:
        """获取所有可用主题。"""
        return list(self._available.values())

    def get(self, theme_id: str) -> Optional[Theme]:
        """按 ID 获取主题。"""
        return self._available.get(theme_id)

    # ── 切换 ──

    def switch_theme(self, theme_id: str) -> bool:
        """切换到指定主题，持久化并发出信号。"""
        if theme_id not in self._available:
            logger.warning(f"主题不存在: {theme_id}")
            return False

        if theme_id == self._current_id:
            return True  # 同一主题，无需切换

        old_id = self._current_id
        self._current_id = theme_id
        self._save()

        logger.info(f"主题切换: {self._available[old_id].name} → "
                     f"{self._available[theme_id].name}")
        self.theme_changed.emit(theme_id)
        return True

    # ── 持久化 ──

    def _load(self):
        """从 themes.json 加载当前主题 ID。"""
        if not os.path.exists(THEMES_FILE):
            return

        try:
            with open(THEMES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            saved_id = data.get("current_theme", "glass")
            if saved_id in self._available:
                self._current_id = saved_id
            else:
                logger.warning(f"保存的主题 '{saved_id}' 不存在，回退到 glass")
                self._current_id = "glass"

            logger.info(f"加载主题配置: {self._current_id}")

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"加载 themes.json 失败: {e}")

    def _save(self):
        """保存当前主题 ID 到 themes.json。"""
        data = {"current_theme": self._current_id}
        try:
            with open(THEMES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"保存主题: {self._current_id}")
        except IOError as e:
            logger.error(f"保存 themes.json 失败: {e}")


# 全局单例
theme_manager = ThemeManager()
