"""独立的问候气泡窗口 — 浮动在宠物上方，不受宠物窗口裁剪"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QPen, QBrush, QFontMetrics
from PyQt5.QtWidgets import QWidget

from .theme import theme_manager


class GreetingBubble(QWidget):
    """独立的问候气泡窗口，浮动在宠物上方。"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._text = ""
        self._pet_window = None
        
        # 自动隐藏定时器
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        
        # 位置跟随定时器
        self._follow_timer = QTimer(self)
        self._follow_timer.timeout.connect(self._update_position)
        self._follow_timer.setInterval(50)  # 20fps 跟随
    
    def show_message(self, text: str, pet_window: QWidget, duration: int = 3000):
        """显示问候消息，跟随宠物窗口。"""
        self._text = text
        self._pet_window = pet_window
        
        # 计算气泡大小
        self._calculate_size()
        
        # 定位到宠物上方
        self._update_position()
        
        # 显示
        self.show()
        self.raise_()
        self.repaint()
        
        # 启动位置跟随
        self._follow_timer.start()
        
        # 设置自动隐藏
        self._hide_timer.start(duration)
        
        print(f"[GreetingBubble] 显示: {text[:20]}... 位置: {self.pos()}")
    
    def _calculate_size(self):
        """根据文字计算气泡大小。"""
        font = QFont("Microsoft YaHei", 10)
        metrics = QFontMetrics(font)
        
        # 计算文字区域
        max_width = 250
        text_rect = metrics.boundingRect(
            0, 0, max_width, 100,
            Qt.TextWordWrap, self._text
        )
        
        padding = 12
        bubble_w = min(text_rect.width() + padding * 2, max_width + padding * 2)
        bubble_h = text_rect.height() + padding * 2
        
        # 加上三角箭头的高度
        self.setFixedSize(bubble_w, bubble_h + 10)
    
    def _update_position(self):
        """更新气泡位置到宠物上方。"""
        if not self._pet_window or not self._pet_window.isVisible():
            return
        
        pet_pos = self._pet_window.pos()
        pet_width = self._pet_window.width()
        
        # 气泡居中于宠物上方
        x = pet_pos.x() + (pet_width - self.width()) // 2
        y = pet_pos.y() - self.height() - 5
        
        self.move(x, y)
    
    def hideEvent(self, event):
        """隐藏时停止定时器。"""
        self._follow_timer.stop()
        self._hide_timer.stop()
        super().hideEvent(event)
    
    def paintEvent(self, event):
        """绘制气泡。"""
        if not self._text:
            return

        t = theme_manager.get_current()
        border_color = t.bubble_border if t else "#E0D0F0"
        bg_color = t.bubble_bg if t else "rgba(255, 255, 255, 240)"
        text_color = t.text_color if t else "#2D2D2D"
        radius = t.border_radius if t else 10

        # 解析背景色
        bg_rgba = self._parse_color(bg_color)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 气泡背景
        bubble_rect = self.rect().adjusted(0, 0, 0, -10)

        painter.setPen(QPen(QColor(border_color), 1.5))
        painter.setBrush(QBrush(QColor(*bg_rgba)))

        path = QPainterPath()
        path.addRoundedRect(bubble_rect.x(), bubble_rect.y(),
                           bubble_rect.width(), bubble_rect.height(), radius, radius)

        # 底部三角箭头（指向宠物）
        tri_x = self.width() // 2
        tri_top = bubble_rect.y() + bubble_rect.height()
        path.moveTo(tri_x - 6, tri_top)
        path.lineTo(tri_x, tri_top + 10)
        path.lineTo(tri_x + 6, tri_top)

        painter.drawPath(path)

        # 绘制文字
        font = QFont("Microsoft YaHei", 10)
        painter.setFont(font)
        painter.setPen(QColor(text_color))

        padding = 12
        painter.drawText(
            bubble_rect.x() + padding,
            bubble_rect.y() + padding,
            bubble_rect.width() - padding * 2,
            bubble_rect.height() - padding * 2,
            Qt.TextWordWrap, self._text
        )

        painter.end()

    @staticmethod
    def _parse_color(color_str: str) -> tuple:
        """解析颜色字符串为 (r, g, b, a) 元组。"""
        s = color_str.strip()
        if s.startswith("rgba("):
            s = s[5:-1]
            return tuple(int(x.strip()) for x in s.split(","))
        elif s.startswith("rgb("):
            s = s[4:-1]
            return (*tuple(int(x.strip()) for x in s.split(",")), 255)
        elif s.startswith("#"):
            s = s.lstrip('#')
            if len(s) == 6:
                return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255
            elif len(s) == 8:
                return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)
        return (255, 255, 255, 240)
