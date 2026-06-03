"""系统托盘图标模块"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication

from .theme import theme_manager
from .glass_effect import apply_acrylic_effect, is_available as glass_available


def _create_tray_icon_pixmap() -> QPixmap:
    """生成一个简单的托盘图标（32x32 圆形 + H 字母），颜色跟随当前主题。"""
    t = theme_manager.get_current()
    bg_color = t.tray_icon_bg if t else "#B088C0"
    text_color = t.tray_icon_text_color if t else "#FFFFFF"

    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(bg_color)))
    painter.drawEllipse(2, 2, size - 4, size - 4)

    painter.setPen(QPen(QColor(text_color), 2))
    font = QFont("Arial", 16, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "H")

    painter.end()
    return pixmap


class TrayIcon(QSystemTrayIcon):
    """系统托盘图标。"""

    show_pet_clicked = pyqtSignal()   # 显示小赫
    restart_clicked = pyqtSignal()    # 重启应用
    theme_changed = pyqtSignal(str)   # 主题切换（转发到 main.py）

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setToolTip("Hermes Desktop Pet")

        self._show_action: QAction | None = None
        self._toggle_action: QAction | None = None
        self._restart_action: QAction | None = None
        self._quit_action: QAction | None = None
        self._theme_menu: QMenu | None = None
        self._toggle_callbacks: list = []  # 保存 toggle 回调列表

        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_theme_menu(self, parent_menu: QMenu) -> QMenu:
        """构建主题子菜单。"""
        t = theme_manager.get_current()
        current_id = theme_manager.current_id

        theme_menu = parent_menu.addMenu("主题")
        theme_menu.setStyleSheet(self._get_submenu_stylesheet())  # 子菜单也要单独设置主题样式

        for theme in theme_manager.get_all():
            action = QAction(f"✨ {theme.name}", self)
            action.setCheckable(True)
            action.setChecked(theme.id == current_id)
            action.triggered.connect(
                lambda checked, tid=theme.id: self._on_theme_selected(tid)
            )
            theme_menu.addAction(action)

        self._theme_menu = theme_menu
        return theme_menu

    @staticmethod
    def _get_menu_stylesheet() -> str:
        """返回基于当前主题的菜单样式表。"""
        t = theme_manager.get_current()
        if not t:
            return ""
        if t.glass_effect:
            bg_color = "rgba(255, 255, 255, 218)"
            border_color = "rgba(255, 255, 255, 170)"
            text_color = "#1F2933"
            hover_bg = "rgba(232, 222, 248, 210)"
            secondary_color = "#5F6B76"
            separator_color = "rgba(176, 136, 192, 120)"
        else:
            bg_color = t.menu_bg
            border_color = t.menu_border
            text_color = t.text_color
            hover_bg = t.menu_item_hover_bg
            secondary_color = t.text_secondary
            separator_color = t.separator_color
        return f"""
            QMenu {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: {t.menu_border_radius}px;
                padding: 4px;
                font-family: 'Microsoft YaHei';
                font-size: {t.menu_font_size}px;
            }}
            QMenu::item {{
                padding: 8px 38px 8px 18px;
                border-radius: 4px;
                color: {text_color};
                min-width: 112px;
            }}
            QMenu::item:selected {{
                background-color: {hover_bg};
                color: {text_color};
            }}
            QMenu::separator {{
                height: 1px;
                background: {separator_color};
                margin: 4px 8px;
            }}
            QMenu::item:disabled {{
                color: {secondary_color};
            }}
            QMenu::item:submenu-indicator {{
                width: 12px;
                height: 12px;
                padding-right: 8px;
            }}
        """
    
    @staticmethod
    def _get_submenu_stylesheet() -> str:
        """返回子菜单样式表：子菜单必须跟随当前主题。"""
        # QMenu 的样式不会自动继承到子菜单，因此这里复用主题化菜单样式。
        return TrayIcon._get_menu_stylesheet()

    def _apply_menu_glass_effects(self, *menus: QMenu) -> None:
        """为托盘主菜单和子菜单应用 Acrylic，QMenu 不会继承窗口效果。"""
        t = theme_manager.get_current()
        if not (t and t.glass_effect and glass_available()):
            return
        for menu in menus:
            apply_acrylic_effect(menu, 0xB8FFFFFF)

    def _build_menu(self):
        """构建/重建托盘菜单（响应主题切换时调用）。"""
        self._menu = QMenu()
        self._menu.setStyleSheet(self._get_menu_stylesheet())

        # 显示小赫
        self._show_action = QAction("显示小赫", self)
        self._show_action.triggered.connect(self.show_pet_clicked.emit)
        self._menu.addAction(self._show_action)

        self._menu.addSeparator()

        # 显示/隐藏聊天
        self._toggle_action = QAction("显示/隐藏聊天", self)
        self._menu.addAction(self._toggle_action)

        self._menu.addSeparator()

        # 主题子菜单
        theme_menu = self._build_theme_menu(self._menu)
        self._apply_menu_glass_effects(self._menu, theme_menu)

        self._menu.addSeparator()

        # 重启
        self._restart_action = QAction("重启", self)
        self._restart_action.triggered.connect(self.restart_clicked.emit)
        self._menu.addAction(self._restart_action)

        # 退出
        self._quit_action = QAction("退出", self)
        self._quit_action.triggered.connect(QApplication.quit)
        self._menu.addAction(self._quit_action)

        # 重新连接保存的 toggle 回调
        for cb in self._toggle_callbacks:
            if self._toggle_action:
                self._toggle_action.triggered.connect(cb)

        self.setContextMenu(self._menu)

        # 更新图标
        self.update_icon()

    def update_icon(self):
        """更新托盘图标以匹配当前主题。"""
        pixmap = _create_tray_icon_pixmap()
        self.setIcon(QIcon(pixmap))

    def update_theme(self, theme_id: str | None = None):
        """响应主题切换，重建菜单和图标。"""
        # 重建菜单（需要断开旧的点击连接，最简单是重建）
        self._build_menu()
        # 更新图标颜色
        self.update_icon()

    def _on_theme_selected(self, theme_id: str):
        """托盘选择主题后的回调。"""
        if theme_manager.switch_theme(theme_id):
            self.theme_changed.emit(theme_id)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_pet_clicked.emit()

    def connect_toggle(self, callback):
        """连接切换聊天窗口回调（支持多次调用，重建菜单时自动重连）。"""
        self._toggle_callbacks.append(callback)
        if self._toggle_action:
            self._toggle_action.triggered.connect(callback)
