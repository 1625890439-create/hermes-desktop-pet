"""桌面宠物主窗口 — 单帧插画 + 程序化动画 + 点击互动"""

import os
import math
import random
from PyQt5.QtCore import Qt, QPoint, QTimer, QRect, QPointF
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPen, QBrush,
    QPainterPath, QTransform, QRegion
)
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QApplication, QLabel

from . import config


class PetWindow(QWidget):
    """透明无边框桌面宠物窗口，显示小天使插画 + 程序化动画。"""

    # 皮肤注册表：名称 → 图片文件名
    SKINS = {
        "小天使": "angel_sprite.png",
        "帅仓鼠": "hamster.png",
    }

    GREETINGS = [
        "主人好呀～(◕ᴗ◕✿)",
        "嘿嘿，主人来了！✧(≖ ◡ ≖✿)",
        "想小赫了吗～♪(´ε` )",
        "主人今天也要加油哦！(ง •̀_•́)ง",
        "小赫一直在等你呢 (´;ω;`)",
        "诶嘿～有什么需要帮忙的吗？",
        "主人好！小赫好开心 (≧▽≦)",
        "今天天气怎么样呀～",
        "主人累了吗？要不要休息一下～",
        "小赫随时待命！✧٩(>ω<*)و✧",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hermes Desktop Pet")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 拖拽状态
        self._drag_pos: QPoint | None = None
        self._drag_moved = False

        # 当前皮肤
        self._current_skin = "小天使"

        # 加载角色图片
        self._pixmap: QPixmap | None = None
        self._load_character()

        # 动画参数
        self._anim_tick = 0          # 动画计时器
        self._bob_offset_y = 0       # 上下浮动偏移
        self._blink_timer = 0        # 眨眼计时
        self._is_blinking = False
        self._breath_scale = 1.0     # 呼吸缩放
        self._bounce_y = 0           # 点击弹跳
        self._bounce_vy = 0          # 弹跳速度

        # 动画定时器 — 33ms ≈ 30fps
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.setInterval(33)

        # 问候气泡
        self._greeting_text = ""
        self._greeting_timer = QTimer(self)
        self._greeting_timer.setSingleShot(True)
        self._greeting_timer.timeout.connect(self._hide_greeting)

        # 思考状态
        self._thinking = False

        # 随机行为定时器（眨眼、歪头等）
        self._random_action_timer = QTimer(self)
        self._random_action_timer.timeout.connect(self._random_action)
        self._random_action_timer.start(random.randint(2000, 5000))

        # 放置到屏幕右下角
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.width() - 40,
                  screen.height() - self.height() - 60)

        # 启动动画
        self._anim_timer.start()

    def _load_character(self):
        """加载角色插画（单帧 PNG，自动裁剪空白边缘）。"""
        filename = self.SKINS.get(self._current_skin, "angel_sprite.png")
        sprite_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assets", filename
        )
        if not os.path.exists(sprite_path):
            self.setFixedSize(config.PET_WIDTH, config.PET_HEIGHT)
            return

        original = QPixmap(sprite_path)
        # 自动裁剪空白边缘（灰白色背景）
        self._pixmap = self._trim_whitespace(original)

        # 缩放到目标高度，保持比例
        target_h = config.PET_HEIGHT
        aspect = self._pixmap.width() / self._pixmap.height()
        target_w = max(int(target_h * aspect), 60)
        self.setFixedSize(target_w, target_h + 40)  # +40 留给气泡空间

    def _trim_whitespace(self, pixmap: QPixmap) -> QPixmap:
        """裁剪图片四周的灰白背景，保留核心内容。"""
        from PyQt5.QtGui import QImage
        img = pixmap.toImage()
        w, h = img.width(), img.height()

        # 采样四个角获取背景色
        corners = [
            img.pixelColor(0, 0),
            img.pixelColor(w - 1, 0),
            img.pixelColor(0, h - 1),
            img.pixelColor(w - 1, h - 1),
        ]
        # 取左上角作为背景参考色
        bg = corners[0]
        bg_r, bg_g, bg_b = bg.red(), bg.green(), bg.blue()

        def is_bg_pixel(x, y):
            c = img.pixelColor(x, y)
            return (abs(c.red() - bg_r) < 25 and
                    abs(c.green() - bg_g) < 25 and
                    abs(c.blue() - bg_b) < 25)

        # 找内容边界
        top = 0
        for y in range(h):
            if not all(is_bg_pixel(x, y) for x in range(0, w, max(1, w // 20))):
                top = y
                break

        bottom = h - 1
        for y in range(h - 1, -1, -1):
            if not all(is_bg_pixel(x, y) for x in range(0, w, max(1, w // 20))):
                bottom = y
                break

        left = 0
        for x in range(w):
            if not all(is_bg_pixel(x, y) for y in range(0, h, max(1, h // 20))):
                left = x
                break

        right = w - 1
        for x in range(w - 1, -1, -1):
            if not all(is_bg_pixel(x, y) for y in range(0, h, max(1, h // 20))):
                right = x
                break

        # 加一点边距
        margin = 5
        left = max(0, left - margin)
        top = max(0, top - margin)
        right = min(w - 1, right + margin)
        bottom = min(h - 1, bottom + margin)

        crop_w = right - left + 1
        crop_h = bottom - top + 1
        if crop_w < 20 or crop_h < 20:
            return pixmap  # 裁剪异常，返回原图

        cropped = pixmap.copy(left, top, crop_w, crop_h)
        print(f"[Pet] 裁剪: 原图 {w}x{h} → 内容 {crop_w}x{crop_h} (offset: {left},{top})")
        return cropped

    # ── 程序化动画 ──

    def _animate(self):
        """每帧更新动画参数。"""
        self._anim_tick += 1
        t = self._anim_tick

        # 上下浮动（正弦波，周期约2秒）
        self._bob_offset_y = math.sin(t * 0.08) * 4

        # 呼吸缩放（很微小，周期约3秒）
        self._breath_scale = 1.0 + math.sin(t * 0.05) * 0.008

        # 弹跳物理
        if abs(self._bounce_vy) > 0.1 or abs(self._bounce_y) > 0.1:
            self._bounce_vy += 0.8  # 重力
            self._bounce_y += self._bounce_vy
            if self._bounce_y > 0:
                self._bounce_y = 0
                self._bounce_vy = -self._bounce_vy * 0.4  # 反弹衰减
                if abs(self._bounce_vy) < 1:
                    self._bounce_vy = 0

        # 思考时抖动
        if self._thinking:
            import math as m
            self._bob_offset_y += math.sin(t * 0.3) * 2

        self.update()

    def _random_action(self):
        """随机行为：眨眼等。"""
        if random.random() < 0.6:
            self._is_blinking = True
            QTimer.singleShot(150, self._unblink)

        # 下次随机行为间隔
        self._random_action_timer.setInterval(random.randint(2000, 6000))

    def _unblink(self):
        self._is_blinking = False

    # ── 思考动画控制 ──

    def start_thinking(self):
        self._thinking = True
        self.update()

    def stop_thinking(self):
        self._thinking = False
        self.update()

    # ── 问候气泡 ──

    def show_greeting(self):
        """显示随机问候语。"""
        self._greeting_text = random.choice(self.GREETINGS)
        # 弹跳效果
        self._bounce_vy = -8
        self.update()
        self._greeting_timer.start(3000)

    def _hide_greeting(self):
        self._greeting_text = ""
        self.update()

    # ── 皮肤切换 ──

    def switch_skin(self, skin_name: str):
        """切换到指定皮肤。"""
        if skin_name in self.SKINS and skin_name != self._current_skin:
            self._current_skin = skin_name
            self._load_character()
            self.update()
            print(f"[Pet] 切换皮肤: {skin_name}")

    # ── 鼠标事件 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._drag_moved = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            self._drag_moved = True
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._drag_pos and not self._drag_moved:
                self._on_click()
            self._drag_pos = None
            event.accept()

    def _on_click(self):
        """点击角色。"""
        self.show_greeting()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFF;
                border: 1px solid #D0C0E0;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Microsoft YaHei';
                font-size: 12px;
            }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #E8DEF8; }
        """)

        toggle_action = QAction("显示/隐藏聊天", self)
        toggle_action.triggered.connect(self._toggle_chat)
        menu.addAction(toggle_action)

        hide_action = QAction("隐藏小赫", self)
        hide_action.triggered.connect(self._hide_all)
        menu.addAction(hide_action)

        menu.addSeparator()

        # 皮肤切换子菜单
        skin_menu = menu.addMenu("切换皮肤")
        for skin_name in self.SKINS:
            action = QAction(skin_name, self)
            action.setCheckable(True)
            action.setChecked(skin_name == self._current_skin)
            action.triggered.connect(lambda checked, n=skin_name: self.switch_skin(n))
            skin_menu.addAction(action)

        menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        menu.exec_(event.globalPos())

    def _toggle_chat(self):
        pass

    def _hide_all(self):
        pass

    # ── 绘制 ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._pixmap and not self._pixmap.isNull():
            # 计算绘制区域（排除气泡空间上方留白）
            draw_h = self.height() - 40  # 气泡空间
            draw_w = self.width()

            # 缩放角色图
            aspect = self._pixmap.width() / self._pixmap.height()
            target_h = int(draw_h * self._breath_scale)
            target_w = int(target_h * aspect)

            if target_w > draw_w:
                target_w = draw_w
                target_h = int(target_w / aspect)

            scaled = self._pixmap.scaled(
                target_w, target_h,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # 居中 + 浮动 + 弹跳
            x = (draw_w - scaled.width()) // 2
            y = 40 + (draw_h - scaled.height()) // 2 + int(self._bob_offset_y + self._bounce_y)

            # 思考时轻微左右摇摆
            if self._thinking:
                x += int(math.sin(self._anim_tick * 0.15) * 3)

            painter.drawPixmap(x, y, scaled)

            # 眨眼效果：在眼睛区域画一个小遮罩（仅视觉提示）
            if self._is_blinking:
                # 在角色上方画两个小短线表示闭眼
                eye_y = y + int(target_h * 0.28)
                eye_lx = x + int(target_w * 0.40)
                eye_rx = x + int(target_w * 0.60)
                painter.setPen(QPen(QColor("#8B6FA8"), 2.5, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(eye_lx - 4, eye_y, eye_lx + 4, eye_y)
                painter.drawLine(eye_rx - 4, eye_y, eye_rx + 4, eye_y)

            # 思考指示：头顶画省略号
            if self._thinking:
                dot_y = y - 12
                dot_x = x + target_w // 2
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor("#B088C0"))
                for i in range(3):
                    dx = dot_x + (i - 1) * 10
                    dy = dot_y + int(math.sin(self._anim_tick * 0.1 + i) * 3)
                    painter.drawEllipse(dx - 3, dy - 3, 6, 6)

        else:
            # 没有图片时绘制占位
            painter.setPen(QPen(QColor("#B088C0"), 2))
            painter.setBrush(QBrush(QColor("#F0E6FF")))
            painter.drawEllipse(10, 50, self.width() - 20, self.height() - 60)
            painter.setFont(QFont("Microsoft YaHei", 24))
            painter.drawText(self.rect(), Qt.AlignCenter, "👼")

        # 绘制问候气泡
        if self._greeting_text:
            self._draw_greeting_bubble(painter)

        painter.end()

    def _draw_greeting_bubble(self, p: QPainter):
        """绘制问候语气泡。"""
        font = QFont("Microsoft YaHei", 10)
        p.setFont(font)
        metrics = p.fontMetrics()
        text_rect = metrics.boundingRect(
            0, 0, 300, 100, Qt.TextWordWrap, self._greeting_text
        )
        padding = 10
        bubble_w = min(text_rect.width() + padding * 2, 300)
        bubble_h = text_rect.height() + padding * 2

        # 气泡位置（窗口顶部）
        bubble_x = (self.width() - bubble_w) // 2
        bubble_y = 2

        # 绘制气泡背景
        p.setPen(QPen(QColor("#E0D0F0"), 1.5))
        p.setBrush(QBrush(QColor(255, 255, 255, 235)))
        path = QPainterPath()
        r = 10
        path.addRoundedRect(bubble_x, bubble_y, bubble_w, bubble_h, r, r)

        # 小三角指向角色
        tri_x = self.width() // 2
        tri_top = bubble_y + bubble_h
        path.moveTo(tri_x - 6, tri_top)
        path.lineTo(tri_x, tri_top + 8)
        path.lineTo(tri_x + 6, tri_top)

        p.drawPath(path)

        # 绘制文字
        p.setPen(QColor("#2D2D2D"))
        p.drawText(
            bubble_x + padding, bubble_y + padding,
            text_rect.width(), text_rect.height(),
            Qt.TextWordWrap, self._greeting_text
        )
