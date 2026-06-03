"""聊天气泡组件 — 对话界面（支持文字选择 + 窗口缩放 + 主题）"""

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QPen, QBrush, QCursor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QScrollArea, QLabel, QFrame, QApplication, QSizePolicy,
    QGraphicsDropShadowEffect
)

from . import config
from .personas import persona_manager
from .theme import theme_manager, Theme
from .glass_effect import apply_acrylic_effect, remove_effects, is_available as glass_available


# 缩放方向常量
_RESIZE_MARGIN = 8  # 边缘拖拽区域宽度


def _get_theme() -> Theme:
    """获取当前主题，若管理器尚未初始化则返回预设 glass 主题。"""
    t = theme_manager.get_current()
    return t if t else theme_manager.get("glass") or Theme()


class MessageLabel(QLabel):
    """单条消息标签，支持圆角背景和文字选择。"""

    def __init__(self, text: str, is_user: bool, theme_color: str = "#B088C0", parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._theme_color = theme_color
        self.setWordWrap(True)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.setMargin(0)

        font = QFont(config.FONT_FAMILY, config.FONT_SIZE_CHAT)
        self.setFont(font)

        self._full_text = text
        self.setText(text)
        self._apply_style()

    def _apply_style(self):
        theme = _get_theme()
        if self.is_user:
            bg = theme.user_msg_bg
        else:
            bg = self._lighten_color(self._theme_color, 1.6)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {theme.text_color};
                border-radius: {theme.border_radius}px;
                padding: {theme.padding_v}px {theme.padding_h}px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_CHAT}px;
                selection-background-color: {theme.selection_bg};
            }}
        """)

    @staticmethod
    def _lighten_color(hex_color: str, factor: float) -> str:
        """将颜色变浅"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"


class StreamingLabel(QLabel):
    """Hermes 流式回复标签，支持逐字追加，结束后可选中复制。"""

    def __init__(self, theme_color: str = "#B088C0", parent=None):
        super().__init__(parent)
        self._buffer = ""
        self._theme_color = theme_color
        self._finished = False
        self.setWordWrap(True)
        font = QFont(config.FONT_FAMILY, config.FONT_SIZE_CHAT)
        self.setFont(font)
        theme = _get_theme()
        bg = self._lighten_color(theme_color, 1.6)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {theme.text_color};
                border-radius: {theme.border_radius}px;
                padding: {theme.padding_v}px {theme.padding_h}px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_CHAT}px;
                selection-background-color: {theme.selection_bg};
            }}
        """)

    @staticmethod
    def _lighten_color(hex_color: str, factor: float) -> str:
        """将颜色变浅"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
        self.setText("")

    def append_text(self, text: str):
        self._buffer += text
        self.setText(self._buffer)

    def get_full_text(self) -> str:
        return self._buffer

    def finish(self):
        """流式结束，启用文字选择。"""
        self._finished = True
        self.setText(self._buffer)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )


class ChatBubble(QWidget):
    """聊天气泡窗口，支持文字复制和手动缩放。"""
    # 信号：用户发送了消息 / 语音输入 / 语音开关 / 重启
    message_sent = pyqtSignal(str)
    mic_clicked = pyqtSignal()        # 麦克风按钮点击
    voice_toggled = pyqtSignal(bool)  # 语音播报开关
    restart_clicked = pyqtSignal()    # 重启按钮点击

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hermes 聊天")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 主题色
        current_persona = persona_manager.get_current()
        self._theme_color = current_persona.theme_color if current_persona else "#B088C0"

        # 当前主题引用
        self._current_theme = _get_theme()
        # 阴影效果对象（动态创建/销毁）
        self._shadow_effect: QGraphicsDropShadowEffect | None = None

        # 应用毛玻璃效果
        self._apply_glass_effect()

        # 最小尺寸 + 可缩放
        self.setMinimumSize(280, 360)
        self.resize(config.CHAT_WIDTH, config.CHAT_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 缩放状态
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        self._hover_edge = None  # 悬停的边缘

        # 输入框拖拽调整大小状态
        self._input_resizing = False
        self._input_resize_start_y = None
        self._input_resize_start_height = None
        self._input_user_resized = False  # 用户是否手动调整过输入框高度

        # 记录初始尺寸用于计算缩放比例
        self._base_width = config.CHAT_WIDTH
        self._base_height = config.CHAT_HEIGHT
        self._base_font_size = config.FONT_SIZE_CHAT
        self._base_input_font_size = config.FONT_SIZE_INPUT
        self._base_max_msg_width = 260  # 消息气泡最大宽度基准

        self._streaming_label: StreamingLabel | None = None
        self._message_labels: list[MessageLabel] = []  # 追踪所有消息标签
        self._msg_wrappers: list[tuple[QWidget, int, int, int, int]] = []  # (wrapper, l, t, r, b) 追踪消息容器
        self._setup_ui()
        # 应用阴影效果（需要在 _setup_ui 之后，因为 _container 要存在）
        self._apply_shadow_effect()

    def _setup_ui(self):
        t = self._current_theme

        # 外层容器 — 用布局填充整个窗口，跟随缩放
        self._container = QWidget(self)
        self._container.setStyleSheet(f"""
            QWidget {{
                background-color: {t.bubble_bg};
                border: 1.5px solid {t.bubble_border};
                border-radius: {t.bubble_border_radius}px;
            }}
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(t.padding_h, 10, t.padding_h, 10)
        layout.setSpacing(t.spacing)

        # 标题栏（可拖拽移动窗口）
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(32)
        self._title_bar.setStyleSheet("background: transparent; border: none;")
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("💬 Hermes 助手")
        title_label.setFont(QFont(config.FONT_FAMILY, 13, QFont.Bold))
        title_label.setStyleSheet(
            f"color: {t.title_color}; border: none; background: transparent;"
        )
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 重启按钮
        restart_btn = QPushButton("🔄")
        restart_btn.setFixedSize(28, 28)
        restart_btn.setCursor(Qt.PointingHandCursor)
        restart_btn.setToolTip("重启应用")
        restart_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                font-size: 14px; color: {t.titlebar_btn_color}; border-radius: 14px;
            }}
            QPushButton:hover {{
                background-color: {t.titlebar_btn_hover_bg}; color: {t.titlebar_btn_hover_text};
            }}
        """)
        restart_btn.clicked.connect(self._on_restart)
        title_layout.addWidget(restart_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                font-size: 16px; color: {t.titlebar_btn_color}; border-radius: 14px;
            }}
            QPushButton:hover {{
                background-color: {t.close_btn_hover_bg}; color: {t.close_btn_hover_text};
            }}
        """)
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        layout.addWidget(self._title_bar)

        # 上下文信息栏
        self._context_label = QLabel("")
        self._context_label.setFont(QFont(config.FONT_FAMILY, 10))
        self._context_label.setStyleSheet(
            f"color: {t.text_secondary}; border: none; background: transparent; padding: 0 4px;"
        )
        layout.addWidget(self._context_label)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(
            f"background-color: {t.separator_color}; max-height: 1px; border: none;"
        )
        layout.addWidget(sep)

        # 消息滚动区域
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                width: {t.scrollbar_width}px; background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {t.scrollbar_handle};
                border-radius: {t.scrollbar_handle_radius}px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self._msg_container = QWidget()
        self._msg_container.setStyleSheet("background: transparent; border: none;")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(4, 4, 4, 4)
        self._msg_layout.setSpacing(8)
        self._msg_layout.addStretch()

        self._scroll.setWidget(self._msg_container)
        layout.addWidget(self._scroll, 1)

        # 输入框调整大小手柄
        self._input_resize_handle = QWidget()
        self._input_resize_handle.setFixedHeight(6)
        self._input_resize_handle.setCursor(Qt.SizeVerCursor)
        self._input_resize_handle.setStyleSheet("""
            QWidget {
                background: transparent;
            }
            QWidget:hover {
                background-color: rgba(128, 128, 128, 0.3);
            }
        """)
        self._input_resize_handle.installEventFilter(self)
        layout.addWidget(self._input_resize_handle)

        # 底部输入区域
        input_bar = QHBoxLayout()
        input_bar.setSpacing(6)

        self._input = QTextEdit()
        self._input.setPlaceholderText("输入消息...")
        self._input.setMinimumHeight(50)  # 增加最小高度确保文字显示
        self._input.setMaximumHeight(300)  # 最大高度限制
        self._input.setFont(QFont(config.FONT_FAMILY, config.FONT_SIZE_INPUT))
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t.input_bg};
                border: 1.5px solid {t.input_border};
                border-radius: {t.border_radius}px;
                padding: 6px {t.padding_h}px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_INPUT}px;
                color: {t.text_color};
            }}
            QTextEdit:focus {{ border-color: {t.input_focus_border}; }}
        """)
        self._input.installEventFilter(self)
        input_bar.addWidget(self._input, 1)

        self._send_btn = QPushButton("发送")
        self._send_btn.setFixedSize(60, 44)
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.setFont(QFont(config.FONT_FAMILY, config.FONT_SIZE_INPUT, QFont.Bold))
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.send_btn_bg};
                color: {t.send_btn_text}; border: none;
                border-radius: {t.border_radius}px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_INPUT}px;
            }}
            QPushButton:hover {{ background-color: {t.send_btn_hover}; }}
            QPushButton:pressed {{ background-color: {t.send_btn_pressed}; }}
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_bar.addWidget(self._send_btn)

        # 麦克风按钮
        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setFixedSize(44, 44)
        self._mic_btn.setCursor(Qt.PointingHandCursor)
        self._mic_btn.setToolTip("语音输入（点击后说话）")
        self._mic_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.mic_btn_bg};
                border: 1.5px solid {t.mic_btn_border};
                border-radius: {t.border_radius}px;
                font-size: 18px;
            }}
            QPushButton:hover {{ background-color: {t.mic_btn_hover}; }}
            QPushButton:pressed {{ background-color: {t.mic_btn_pressed}; }}
        """)
        self._mic_btn.clicked.connect(self._on_mic)
        input_bar.addWidget(self._mic_btn)

        # 语音播报开关
        self._voice_btn = QPushButton("🔊")
        self._voice_btn.setFixedSize(44, 44)
        self._voice_btn.setCursor(Qt.PointingHandCursor)
        self._voice_btn.setToolTip("语音播报开关")
        self._voice_btn.setCheckable(True)
        self._voice_btn.setChecked(True)
        self._voice_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.voice_btn_bg};
                border: 1.5px solid {t.voice_btn_border};
                border-radius: {t.border_radius}px;
                font-size: 18px;
            }}
            QPushButton:checked {{
                background-color: {t.voice_btn_checked_bg};
                border-color: {t.voice_btn_checked_border};
            }}
            QPushButton:hover {{ background-color: {t.voice_btn_hover}; }}
        """)
        self._voice_btn.clicked.connect(self._on_voice_toggle)
        input_bar.addWidget(self._voice_btn)

        layout.addLayout(input_bar)

    # ── 标题栏拖拽移动窗口 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 检查是否在边缘区域（缩放）
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resize_edge = edge
                self._resize_start_pos = event.globalPos()
                self._resize_start_geo = self.geometry()
                event.accept()
                return

            # 标题栏区域拖拽移动
            if event.pos().y() < self._title_bar.height() + 10:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            # 缩放处理
            if self._resize_edge and self._resize_start_geo:
                self._do_resize(event.globalPos())
                event.accept()
                return

            # 拖拽移动
            if hasattr(self, '_drag_pos') and self._drag_pos:
                self.move(event.globalPos() - self._drag_pos)
                event.accept()
                return

        # 更新鼠标样式（悬停边缘时）
        edge = self._get_resize_edge(event.pos())
        if edge != self._hover_edge:
            self._hover_edge = edge
            self.update()  # 触发重绘
        if edge:
            cursors = {
                "left": Qt.SizeHorCursor, "right": Qt.SizeHorCursor,
                "top": Qt.SizeVerCursor, "bottom": Qt.SizeVerCursor,
                "top-left": Qt.SizeFDiagCursor, "top-right": Qt.SizeBDiagCursor,
                "bottom-left": Qt.SizeBDiagCursor, "bottom-right": Qt.SizeFDiagCursor,
            }
            self.setCursor(cursors.get(edge, Qt.ArrowCursor))
        else:
            self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        if hasattr(self, '_drag_pos'):
            self._drag_pos = None
        event.accept()

    def leaveEvent(self, event):
        """鼠标离开窗口时清除边缘高亮。"""
        if self._hover_edge:
            self._hover_edge = None
            self.setCursor(Qt.ArrowCursor)
            self.update()

    def resizeEvent(self, event):
        """窗口大小改变时自动更新布局。"""
        super().resizeEvent(event)
        # 延迟更新布局，避免在拖拽过程中频繁触发
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
        else:
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._apply_resize_layout)
        self._resize_timer.start(50)  # 50ms 延迟

    def _apply_resize_layout(self):
        """应用缩放后的布局更新。"""
        self._update_fonts_on_resize(self.width(), self.height())

    def _get_resize_edge(self, pos: QPoint) -> str | None:
        """判断鼠标位置是否在窗口边缘。"""
        w, h = self.width(), self.height()
        m = _RESIZE_MARGIN
        x, y = pos.x(), pos.y()

        left = x < m
        right = x > w - m
        top = y < m
        bottom = y > h - m

        if top and left: return "top-left"
        if top and right: return "top-right"
        if bottom and left: return "bottom-left"
        if bottom and right: return "bottom-right"
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return None

    def _do_resize(self, global_pos: QPoint):
        """执行缩放。"""
        dx = global_pos.x() - self._resize_start_pos.x()
        dy = global_pos.y() - self._resize_start_pos.y()
        geo = self._resize_start_geo
        min_w, min_h = self.minimumWidth(), self.minimumHeight()

        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()

        edge = self._resize_edge
        if "right" in edge:
            w = max(min_w, geo.width() + dx)
        if "bottom" in edge:
            h = max(min_h, geo.height() + dy)
        if "left" in edge:
            new_w = max(min_w, geo.width() - dx)
            x = geo.x() + geo.width() - new_w
            w = new_w
        if "top" in edge:
            new_h = max(min_h, geo.height() - dy)
            y = geo.y() + geo.height() - new_h
            h = new_h

        self.setGeometry(x, y, w, h)
        
        # 根据窗口大小调整字体
        self._update_fonts_on_resize(w, h)

    def _update_fonts_on_resize(self, width: int, height: int):
        """根据窗口大小动态调整字体和气泡尺寸。"""
        scale = width / self._base_width
        scale = max(0.6, min(scale, 4.0))  # 限制缩放范围

        t = self._current_theme

        # 计算新字体大小
        new_chat_font_size = max(10, int(self._base_font_size * scale))
        new_input_font_size = max(10, int(self._base_input_font_size * scale))

        # 计算气泡内边距和圆角（跟随缩放）
        pv = max(4, int(t.padding_v * scale))
        ph = max(6, int(t.padding_h * scale))
        br = max(6, int(t.border_radius * scale))

        # 计算消息气泡最大宽度（跟随缩放）
        max_msg_width = max(150, int(self._base_max_msg_width * scale))

        # 计算主题色背景
        theme_bg = MessageLabel._lighten_color(self._theme_color, 1.6)

        # 更新消息标签的样式
        msg_style = f"""
            QLabel {{
                background-color: {theme_bg};
                color: {t.text_color};
                border-radius: {br}px;
                padding: {pv}px {ph}px;
                font-family: {config.FONT_FAMILY};
                font-size: {new_chat_font_size}px;
                selection-background-color: {t.selection_bg};
            }}
        """
        user_style = f"""
            QLabel {{
                background-color: {t.user_msg_bg};
                color: {t.text_color};
                border-radius: {br}px;
                padding: {pv}px {ph}px;
                font-family: {config.FONT_FAMILY};
                font-size: {new_chat_font_size}px;
                selection-background-color: {t.selection_bg};
            }}
        """

        for label in self._message_labels:
            if hasattr(label, 'is_user') and label.is_user:
                label.setStyleSheet(user_style)
            else:
                label.setStyleSheet(msg_style)
            label.setMaximumWidth(max_msg_width)

        # 更新流式标签的样式
        if self._streaming_label:
            self._streaming_label.setStyleSheet(msg_style)
            self._streaming_label.setMaximumWidth(max_msg_width)

        # 更新消息容器的边距（跟随缩放）
        for wrapper_data in self._msg_wrappers:
            wrapper, base_l, base_t, base_r, base_b = wrapper_data
            new_l = max(10, int(base_l * scale))
            new_t = max(1, int(base_t * scale))
            new_r = max(0, int(base_r * scale))
            new_b = max(1, int(base_b * scale))
            wrapper.layout().setContentsMargins(new_l, new_t, new_r, new_b)

        # 更新输入框和按钮的字体
        input_style = f"""
            QTextEdit {{
                background-color: {t.input_bg};
                border: 1.5px solid {t.input_border};
                border-radius: {br}px;
                padding: {pv}px {ph}px;
                font-family: {config.FONT_FAMILY};
                font-size: {new_input_font_size}px;
                color: {t.text_color};
            }}
            QTextEdit:focus {{ border-color: {t.input_focus_border}; }}
        """
        self._input.setStyleSheet(input_style)

        # 动态调整输入框最大高度（跟随窗口缩放）
        new_input_max_height = max(100, int(height * 0.4))
        self._input.setMaximumHeight(new_input_max_height)
        
        # 如果用户没有手动调整过，恢复最小高度为默认值
        if not self._input_user_resized:
            self._input.setMinimumHeight(50)

        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.send_btn_bg};
                color: {t.send_btn_text}; border: none;
                border-radius: {br}px;
                font-family: {config.FONT_FAMILY};
                font-size: {new_input_font_size}px;
            }}
            QPushButton:hover {{ background-color: {t.send_btn_hover}; }}
            QPushButton:pressed {{ background-color: {t.send_btn_pressed}; }}
        """)

    # ── 其他逻辑 ──

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent

        # 处理输入框调整大小手柄的拖拽
        if obj is self._input_resize_handle:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._input_resizing = True
                self._input_resize_start_y = event.globalPos().y()
                self._input_resize_start_height = self._input.height()
                return True
            elif event.type() == QEvent.MouseMove and self._input_resizing:
                from PyQt5.QtWidgets import QApplication
                dy = event.globalPos().y() - self._input_resize_start_y
                max_height = self._input.maximumHeight()
                new_height = max(50, min(max_height, self._input_resize_start_height - dy))
                # 同时设置最小和最大高度，让布局系统正确响应
                self._input.setMinimumHeight(new_height)
                self._input.setMaximumHeight(new_height)
                # 强制立即处理事件和重绘
                QApplication.processEvents()
                return True
            elif event.type() == QEvent.MouseButtonRelease and self._input_resizing:
                self._input_resizing = False
                self._input_user_resized = True  # 标记用户已手动调整
                self._input_resize_start_y = None
                self._input_resize_start_height = None
                return True

        # 处理输入框回车发送
        if obj is self._input and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if not (event.modifiers() & Qt.ShiftModifier):
                    self._on_send()
                    return True
        return super().eventFilter(obj, event)

    def _on_send(self):
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._input.clear()
        self.add_user_message(text)
        self.message_sent.emit(text)

    def _on_mic(self):
        """麦克风按钮点击。"""
        self._mic_btn.setEnabled(False)
        self._mic_btn.setText("🔴")
        self._mic_btn.setToolTip("正在听...")
        self.mic_clicked.emit()

    def mic_recording_done(self):
        """录音结束，恢复按钮状态。"""
        self._mic_btn.setEnabled(True)
        self._mic_btn.setText("🎤")
        self._mic_btn.setToolTip("语音输入（点击后说话）")

    def mic_recording_error(self, msg: str):
        """录音出错。"""
        self.mic_recording_done()
        self.add_error_message(msg)

    def _on_voice_toggle(self):
        """语音播报开关切换。"""
        enabled = self._voice_btn.isChecked()
        self._voice_btn.setText("🔊" if enabled else "🔇")
        self._voice_btn.setToolTip("语音播报: " + ("开" if enabled else "关"))
        self.voice_toggled.emit(enabled)

    def _on_restart(self):
        """重启按钮点击。"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认重启",
            "确定要重启应用吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.restart_clicked.emit()

    def voice_enabled(self) -> bool:
        return self._voice_btn.isChecked()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _get_current_max_msg_width(self) -> int:
        """获取当前缩放比例下的消息气泡最大宽度"""
        scale = self.width() / self._base_width
        scale = max(0.6, min(scale, 4.0))
        return max(150, int(self._base_max_msg_width * scale))

    def add_user_message(self, text: str):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; border: none;")
        w_layout = QHBoxLayout(wrapper)
        base_l, base_t, base_r, base_b = 30, 2, 0, 2
        w_layout.setContentsMargins(base_l, base_t, base_r, base_b)

        label = MessageLabel(text, is_user=True, theme_color=self._theme_color)
        label.setMaximumWidth(self._get_current_max_msg_width())
        self._message_labels.append(label)  # 追踪标签
        self._msg_wrappers.append((wrapper, base_l, base_t, base_r, base_b))  # 追踪容器
        w_layout.addWidget(label)
        w_layout.addStretch()

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, wrapper)
        self._scroll_to_bottom()
        self._update_fonts_on_resize(self.width(), self.height())

    def start_hermes_message(self):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; border: none;")
        w_layout = QHBoxLayout(wrapper)
        w_layout.setContentsMargins(0, 2, 30, 2)

        # 头像：使用当前persona的皮肤图片
        avatar = QLabel()
        avatar.setFixedSize(28, 28)
        current_persona = persona_manager.get_current()
        if current_persona and current_persona.skin:
            from pathlib import Path
            skin_path = Path(__file__).parent.parent / "assets" / current_persona.skin
            if skin_path.exists():
                from PyQt5.QtGui import QPixmap
                pixmap = QPixmap(str(skin_path)).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                avatar.setPixmap(pixmap)
                avatar.setStyleSheet("background: transparent; border: none;")
            else:
                avatar.setText("🌸")
                avatar.setAlignment(Qt.AlignCenter)
                avatar.setStyleSheet(f"""
                    QLabel {{
                        background-color: {self._theme_color};
                        border-radius: 14px;
                        font-size: 14px;
                        border: none;
                    }}
                """)
        else:
            avatar.setText("🌸")
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setStyleSheet(f"""
                QLabel {{
                    background-color: {self._theme_color};
                    border-radius: 14px;
                    font-size: 14px;
                    border: none;
                }}
            """)
        w_layout.addWidget(avatar, 0, Qt.AlignTop)

        self._streaming_label = StreamingLabel(theme_color=self._theme_color)
        self._streaming_label.setMinimumWidth(60)
        self._streaming_label.setMaximumWidth(self._get_current_max_msg_width())
        w_layout.addWidget(self._streaming_label, 1)
        w_layout.addStretch()

        # 追踪容器（用于缩放时更新边距）
        self._msg_wrappers.append((wrapper, 0, 2, 30, 2))

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, wrapper)
        self._scroll_to_bottom()
        self._update_fonts_on_resize(self.width(), self.height())
        return self._streaming_label

    def append_streaming_text(self, text: str):
        if self._streaming_label:
            self._streaming_label.append_text(text)
            self._scroll_to_bottom()

    def finish_streaming(self):
        if self._streaming_label:
            self._streaming_label.finish()
            reply_text = self._streaming_label.get_full_text()
            self._message_labels.append(self._streaming_label)  # 追踪标签
            self._streaming_label = None
            return reply_text
        return ""

    def add_error_message(self, text: str):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; border: none;")
        w_layout = QHBoxLayout(wrapper)
        w_layout.setContentsMargins(0, 2, 30, 2)

        t = self._current_theme
        label = QLabel(f"⚠️ {text}")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setFont(QFont(config.FONT_FAMILY, config.FONT_SIZE_LABEL))
        label.setStyleSheet(f"""
            QLabel {{
                background-color: {t.error_bg};
                color: {t.error_text};
                border: 1px solid {t.error_border};
                border-radius: {t.border_radius - 2}px;
                padding: {t.padding_v}px {t.padding_h}px;
            }}
        """)
        label.setMaximumWidth(280)
        w_layout.addWidget(label)
        w_layout.addStretch()

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, wrapper)
        self._scroll_to_bottom()

    def update_context_info(self, msg_count: int, char_count: int):
        est_tokens = int(char_count * 1.2)
        self._context_label.setText(f"💬 {msg_count} 条消息 · ~{est_tokens} tokens")

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._hover_edge:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m = _RESIZE_MARGIN
        w, h = self.width(), self.height()
        # 使用主题色作为边缘高亮参考色
        rgba = self._parse_rgba(self._current_theme.input_focus_border)
        color = QColor(rgba[0], rgba[1], rgba[2], 120)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        edge = self._hover_edge
        if "left" in edge:
            p.drawRect(0, 0, m, h)
        if "right" in edge:
            p.drawRect(w - m, 0, m, h)
        if "top" in edge:
            p.drawRect(0, 0, w, m)
        if "bottom" in edge:
            p.drawRect(0, h - m, w, m)
        p.end()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self._input.setFocus()
    
    def update_theme_color(self, color: str):
        """更新主题色并刷新UI（由人格切换触发）"""
        self._theme_color = color
        self._refresh_all_styles()

    # ── 主题切换 ──

    def update_theme(self, theme_id: str | None = None):
        """响应全局主题切换，刷新所有样式。

        Args:
            theme_id: 新主题 ID，若为 None 则从 theme_manager 获取当前主题。
        """
        self._current_theme = _get_theme()
        self._refresh_all_styles()

        # 更新毛玻璃效果
        self._apply_glass_effect()

        # 更新阴影效果
        self._apply_shadow_effect()

        logger = __import__('logging').getLogger(__name__)
        logger.debug(f"ChatBubble 主题已更新: {self._current_theme.name}")

    def _refresh_all_styles(self):
        """重新计算并应用所有组件的样式（基于当前主题 + 主题色）。"""
        t = self._current_theme

        # 容器样式
        self._container.setStyleSheet(f"""
            QWidget {{
                background-color: {t.bubble_bg};
                border: 1.5px solid {t.bubble_border};
                border-radius: {t.bubble_border_radius}px;
            }}
        """)

        # 点击 resize 刷新气泡样式
        if hasattr(self, '_rescaling') and self._rescaling:
            return
        self._update_fonts_on_resize(self.width(), self.height())

    def _apply_glass_effect(self):
        """应用毛玻璃半透明效果。"""
        t = self._current_theme
        if t.glass_effect:
            self.setWindowOpacity(t.background_opacity)
            # 应用真正的 Windows Acrylic 模糊效果
            if glass_available():
                apply_acrylic_effect(self, 0x20FFFFFF)  # 浅色半透明着色
        else:
            self.setWindowOpacity(1.0)
            if glass_available():
                remove_effects(self)

    def _apply_shadow_effect(self):
        """应用/移除窗口阴影效果。"""
        t = self._current_theme

        # 移除旧阴影
        if self._shadow_effect:
            try:
                self._shadow_effect.setEnabled(False)
                self._container.setGraphicsEffect(None)
                self._shadow_effect.deleteLater()
            except RuntimeError:
                pass  # C++ 对象已被删除
            self._shadow_effect = None

        if t.shadow_enabled:
            self._shadow_effect = QGraphicsDropShadowEffect(self)
            self._shadow_effect.setBlurRadius(t.shadow_blur)
            self._shadow_effect.setOffset(t.shadow_offset_x, t.shadow_offset_y)
            self._shadow_effect.setColor(QColor(
                *self._parse_rgba(t.shadow_color)
            ))
            self._container.setGraphicsEffect(self._shadow_effect)

    @staticmethod
    def _parse_rgba(rgba_str: str) -> tuple:
        """解析 'rgba(r, g, b, a)' 或 '#RRGGBB' 字符串为 (r, g, b, a) 元组。"""
        s = rgba_str.strip()
        if s.startswith("rgba("):
            s = s[5:-1]
            parts = [int(x.strip()) for x in s.split(",")]
            return tuple(parts[:4])
        elif s.startswith("rgb("):
            s = s[4:-1]
            parts = [int(x.strip()) for x in s.split(",")]
            return (*parts[:3], 255)
        elif s.startswith("#"):
            s = s.lstrip('#')
            if len(s) == 6:
                return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255
            elif len(s) == 8:
                return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)
        return (0, 0, 0, 255)
    
    @staticmethod
    def _darken_color(hex_color: str, factor: float) -> str:
        """将颜色加深（factor < 1）或变浅（factor > 1）"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    def clear_messages(self):
        """清空所有聊天消息（人格切换时调用）"""
        # 遍历并删除所有消息 widget（保留最后的 stretch）
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 重置流式标签和追踪列表
        self._streaming_label = None
        self._message_labels.clear()
        self._msg_wrappers.clear()
        
        # 重新添加欢迎消息
        self._add_welcome_message()
    
    def _add_welcome_message(self):
        """添加欢迎消息"""
        current_persona = persona_manager.get_current()
        if current_persona:
            welcome_text = f"你好，我是{current_persona.name}，有什么可以帮你的？"
        else:
            welcome_text = "你好，有什么可以帮你的？"
        
        # 使用 Hermes 格式添加消息
        self.start_hermes_message()
        self._streaming_label.append_text(welcome_text)
        self._streaming_label.finish()
