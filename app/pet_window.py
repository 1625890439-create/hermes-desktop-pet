"""桌面宠物主窗口 — 单帧插画 + 程序化动画 + 点击互动"""

import os
import math
import time
import random
from PyQt5.QtCore import Qt, QPoint, QTimer, QRect, QPointF, pyqtSignal
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPen, QBrush,
    QPainterPath, QTransform, QRegion
)
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QApplication, QLabel

from . import config
from .personas import persona_manager
from .theme import theme_manager
from .greeting_bubble import GreetingBubble
from .glass_effect import apply_acrylic_effect, apply_blur_behind, remove_effects, is_available as glass_available
from .sprite_animator import SpriteAnimator, PetState


class PetWindow(QWidget):
    """透明无边框桌面宠物窗口，显示小天使插画 + 程序化动画。"""
    
    # 信号：人格切换（通知 main.py 更新 API 配置）
    persona_changed = pyqtSignal(str)  # 传递人格 ID
    
    # 皮肤注册表：名称 → 图片文件名（兼容旧版）
    SKINS = {
        "小天使": "angel_sprite.png",
        "帅仓鼠": "hamster.png",
    }

    # 皮肤文件名 → 精灵目录（相对于 assets/）的映射
    # 当皮肤有对应精灵资源时，使用多帧动画代替静态图片
    _SPRITE_DIRS = {
        "angel_sprite.png": "sprites",
        "angel_sprite_o.png": "sprites",
        "win大师.png": "sprites",
    }

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

        # 从 persona_manager 加载当前人格
        current_persona = persona_manager.get_current()
        self._current_skin = current_persona.skin if current_persona else "angel_sprite.png"
        self._greetings = current_persona.greetings if current_persona else self._default_greetings()
        self._theme_color = current_persona.theme_color if current_persona else "#B088C0"

        # 加载角色图片
        self._pixmap: QPixmap | None = None
        self._sprite_animator: SpriteAnimator | None = None
        self._load_character()

        # 动画计时（用于精灵帧更新的 dt 计算）
        self._last_anim_time = time.monotonic()

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

        # 独立的问候气泡窗口
        self._greeting_bubble = GreetingBubble()
        
        # 思考状态
        self._thinking = False

        # 拖拽跳跃检测
        self._drag_start_y: int | None = None
        self._is_dragging_up: bool = False
        self._jump_offset_y: int = 0  # 跳跃时形象上移偏移

        # 放置到屏幕右下角
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.width() - 40,
                  screen.height() - self.height() - 60)

        # 启动动画
        self._anim_timer.start()

    def _load_character(self):
        """加载角色形象：优先使用精灵动画，否则回退到单帧 PNG。"""
        # 支持两种方式：1) SKINS 字典中的名称 2) 直接文件名
        if self._current_skin in self.SKINS:
            filename = self.SKINS[self._current_skin]
        else:
            # 直接使用文件名（人格切换时使用）
            filename = self._current_skin

        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

        # ── 尝试加载精灵动画 ──
        self._sprite_animator = None
        sprite_dir_name = self._SPRITE_DIRS.get(filename)
        if sprite_dir_name:
            sprite_root = os.path.join(assets_dir, sprite_dir_name)
            if os.path.isdir(sprite_root):
                animator = SpriteAnimator(sprite_root)
                if animator.is_loaded:
                    self._sprite_animator = animator
                    # 用 idle 第一帧确定窗口尺寸
                    idle_frame = animator.get_idle_frame()
                    if idle_frame:
                        target_h = config.PET_HEIGHT
                        aspect = idle_frame.width() / max(idle_frame.height(), 1)
                        target_w = max(int(target_h * aspect), 60)
                        self.setFixedSize(target_w, target_h)
                        print(f"[Pet] 加载精灵动画: {filename} → {sprite_dir_name}/")
                        return

        # ── 回退：加载单帧 PNG ──
        sprite_path = os.path.join(assets_dir, filename)
        if not os.path.exists(sprite_path):
            print(f"[Pet] 形象图片不存在: {sprite_path}")
            self.setFixedSize(config.PET_WIDTH, config.PET_HEIGHT)
            return

        original = QPixmap(sprite_path)
        # 自动裁剪空白边缘（灰白色背景）
        self._pixmap = self._trim_whitespace(original)

        # 缩放到目标高度，保持比例
        target_h = config.PET_HEIGHT
        aspect = self._pixmap.width() / self._pixmap.height()
        target_w = max(int(target_h * aspect), 60)
        self.setFixedSize(target_w, target_h)
        print(f"[Pet] 加载形象: {filename}")

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

        # 计算实际时间增量（秒），供精灵动画器使用
        now = time.monotonic()
        dt = now - self._last_anim_time
        self._last_anim_time = now

        # 更新精灵动画帧
        if self._sprite_animator:
            self._sprite_animator.update(dt)
            # 精灵模式：不做浮动/呼吸，保持站立静止
            self._bob_offset_y = 0
            self._breath_scale = 1.0
        else:
            # 旧版模式：程序化浮动和呼吸
            self._bob_offset_y = math.sin(t * 0.08) * 4
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

        # 思考时抖动（仅旧版模式）
        if self._thinking and not self._sprite_animator:
            self._bob_offset_y += math.sin(t * 0.3) * 2

        self.update()

    def _random_action(self):
        """随机行为：旧版模式下的眨眼。精灵模式由 animator 自动管理。"""
        if not self._sprite_animator:
            if random.random() < 0.6:
                self._is_blinking = True
                QTimer.singleShot(150, self._unblink)

    def _unblink(self):
        self._is_blinking = False

    # ── 思考动画控制 ──

    def start_thinking(self):
        """开始思考：先讲话第一帧，2秒后切到跑步循环"""
        self._thinking = True
        if self._sprite_animator:
            self._sprite_animator.set_talk_first()
            # 2秒后切到跑步
            QTimer.singleShot(2000, self._switch_to_run)
        self.update()

    def _switch_to_run(self):
        """思考中切换到跑步动画"""
        if self._thinking and self._sprite_animator:
            self._sprite_animator.start_run()

    def stop_thinking(self):
        """停止思考：回到 idle"""
        self._thinking = False
        if self._sprite_animator:
            self._sprite_animator.set_idle()
        self.update()

    def set_talk_last(self):
        """遇到难题：显示讲话最后一帧"""
        if self._sprite_animator:
            self._sprite_animator.set_talk_last()
            self.update()

    def set_problem_solved(self):
        """问题解决：切换到特殊动作第6帧"""
        if self._sprite_animator:
            self._sprite_animator.set_special_6()
            self.update()

    # ── 问候气泡 ──

    def _default_greetings(self):
        """默认问候语"""
        return [
            "你好呀～(◕ᴗ◕✿)",
            "有什么需要帮忙的吗？",
            "我在呢，说吧～",
        ]

    def show_greeting(self):
        """显示随机问候语。"""
        greeting_text = random.choice(self._greetings)
        # 弹跳效果
        self._bounce_vy = -8
        # 精灵模式：播放眨眼动画
        if self._sprite_animator and 'blink' in self._sprite_animator.available_actions:
            self._sprite_animator.play_one_shot('blink', return_action='idle')
        self.update()
        # 使用独立气泡显示
        self._greeting_bubble.show_message(greeting_text, self, duration=3000)

    # ── 皮肤切换 ──

    def switch_skin(self, skin_name: str):
        """切换到指定皮肤（兼容旧版）。"""
        if skin_name in self.SKINS and skin_name != self._current_skin:
            self._current_skin = skin_name
            self._load_character()
            self.update()
            print(f"[Pet] 切换皮肤: {skin_name}")
    
    def switch_persona(self, persona_id: str):
        """切换到指定人格"""
        if persona_manager.switch_to(persona_id):
            persona = persona_manager.get_current()
            if persona:
                # 更新形象
                self._current_skin = persona.skin
                self._load_character()
                
                # 更新问候语
                self._greetings = persona.greetings or self._default_greetings()
                
                # 更新主题色
                self._theme_color = persona.theme_color
                
                # 发送信号通知 main.py 更新 API 配置
                self.persona_changed.emit(persona_id)
                
                # 显示切换成功问候
                self.show_greeting()
                
                print(f"[Pet] 切换人格: {persona.name}")

    # ── 鼠标事件 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._drag_start_y = event.globalPos().y()
            self._drag_moved = False
            self._is_dragging_up = False
            self._jump_offset_y = 0  # 跳跃上移偏移
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            self._drag_moved = True
            # 检测向上拖拽
            if self._drag_start_y is not None:
                dy = self._drag_start_y - event.globalPos().y()
                if dy > 30 and not self._is_dragging_up:
                    self._is_dragging_up = True
                    if self._sprite_animator:
                        self._sprite_animator.start_jump()
                # 拖拽过程中持续上移形象（最多上移40px）
                if self._is_dragging_up:
                    self._jump_offset_y = min(dy - 30, 40)
                    self.update()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._drag_pos and not self._drag_moved:
                self._on_click()
            # 松开：切换到落地阶段
            if self._is_dragging_up and self._sprite_animator:
                self._sprite_animator.release_jump()
                self._jump_offset_y = 0
                self.update()
            self._drag_pos = None
            self._drag_start_y = None
            self._is_dragging_up = False
            event.accept()

    def _on_click(self):
        """点击角色：随机播放特殊动作 004/006/007"""
        if self._sprite_animator and 'special' in self._sprite_animator.available_actions:
            idx = random.choice([4, 6, 7])
            self._sprite_animator._enter_state(PetState.SPECIAL, idx)
        self.show_greeting()

    def _get_menu_stylesheet(self) -> str:
        """返回基于当前主题的右键菜单样式表。"""
        t = theme_manager.get_current()
        if not t:
            return ""
        
        # 毛玻璃主题使用半透明背景
        if t.glass_effect and glass_available():
            bg_color = "rgba(255, 255, 255, 40)"  # 极低不透明度，让 Acrylic 效果显现
            border_color = "rgba(255, 255, 255, 60)"
        else:
            bg_color = t.menu_bg
            border_color = t.menu_border
        
        return f"""
            QMenu {{
                background-color: {bg_color};
                color: {t.text_color};
                border: 1px solid {border_color};
                border-radius: {t.menu_border_radius}px;
                padding: 6px;
                font-family: '{config.FONT_FAMILY}';
                font-size: {t.menu_font_size}px;
            }}
            QMenu::item {{
                padding: 8px 24px 8px 16px;
                border-radius: 6px;
                color: {t.text_color};
                margin: 2px 4px;
            }}
            QMenu::item:selected {{
                background-color: {t.menu_item_hover_bg};
                color: {t.text_color};
            }}
            QMenu::separator {{
                height: 1px;
                background: {t.separator_color};
                margin: 6px 12px;
            }}
            QMenu::item:disabled {{
                color: {t.text_secondary};
            }}
            QMenu::icon {{
                padding-left: 8px;
            }}
        """

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        stylesheet = self._get_menu_stylesheet()
        menu.setStyleSheet(stylesheet)
        
        # 毛玻璃主题应用真正的 Acrylic 效果
        t = theme_manager.get_current()
        if t and t.glass_effect and glass_available():
            # 灰色半透明着色，让背景模糊可见
            apply_acrylic_effect(menu, 0x40C0C0C0)

        toggle_action = QAction("显示/隐藏聊天", self)
        toggle_action.triggered.connect(self._toggle_chat)
        menu.addAction(toggle_action)

        hide_action = QAction("隐藏小赫", self)
        hide_action.triggered.connect(self._hide_all)
        menu.addAction(hide_action)

        menu.addSeparator()

        # 人格切换子菜单
        persona_menu = menu.addMenu("切换人格")
        persona_menu.setStyleSheet(stylesheet)  # 子菜单也要设置样式
        current_persona = persona_manager.get_current()

        for persona in persona_manager.get_all():
            action = QAction(persona.name, self)
            action.setCheckable(True)
            action.setChecked(current_persona and persona.id == current_persona.id)
            action.setToolTip(persona.description or persona.model_name)
            action.triggered.connect(lambda checked, pid=persona.id: self.switch_persona(pid))
            persona_menu.addAction(action)

        persona_menu.addSeparator()

        manage_action = QAction("管理人格...", self)
        manage_action.triggered.connect(self._open_persona_manager)
        persona_menu.addAction(manage_action)

        menu.addSeparator()

        # 皮肤切换子菜单（保留旧版兼容）
        skin_menu = menu.addMenu("切换皮肤")
        skin_menu.setStyleSheet(stylesheet)  # 子菜单也要设置样式
        for skin_name in self.SKINS:
            action = QAction(skin_name, self)
            action.setCheckable(True)
            action.setChecked(skin_name == self._current_skin)
            action.triggered.connect(lambda checked, n=skin_name: self.switch_skin(n))
            skin_menu.addAction(action)

        menu.addSeparator()

        # 主题切换子菜单
        theme_menu = menu.addMenu("主题")
        theme_menu.setStyleSheet(stylesheet)  # 子菜单也要设置样式
        current_theme_id = theme_manager.current_id
        for theme in theme_manager.get_all():
            action = QAction(f"✨ {theme.name}", self)
            action.setCheckable(True)
            action.setChecked(theme.id == current_theme_id)
            action.triggered.connect(lambda checked, tid=theme.id: self._on_theme_selected(tid))
            theme_menu.addAction(action)

        menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        menu.exec_(event.globalPos())

    def _on_theme_selected(self, theme_id: str):
        """右键菜单选择主题后的回调。"""
        theme_manager.switch_theme(theme_id)

    def _toggle_chat(self):
        pass

    def _hide_all(self):
        pass
    
    def _open_persona_manager(self):
        """打开人格管理对话框"""
        from .persona_dialog import PersonaListDialog
        dialog = PersonaListDialog(self)
        dialog.exec_()

    # ── 绘制 ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        # 获取当前要绘制的帧：精灵动画优先，否则用静态图片
        if self._sprite_animator:
            frame = self._sprite_animator.current_frame()
        else:
            frame = self._pixmap

        if frame and not frame.isNull():
            # 计算绘制区域
            draw_h = self.height()
            draw_w = self.width()

            # 缩放帧到窗口大小（保持比例）
            aspect = frame.width() / max(frame.height(), 1)
            target_h = int(draw_h * self._breath_scale)
            target_w = int(target_h * aspect)

            if target_w > draw_w:
                target_w = draw_w
                target_h = int(target_w / aspect)

            scaled = frame.scaled(
                target_w, target_h,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # 居中 + 浮动 + 弹跳 + 跳跃上移
            x = (draw_w - scaled.width()) // 2
            y = (draw_h - scaled.height()) // 2 + int(self._bob_offset_y + self._bounce_y - self._jump_offset_y)

            # 思考时轻微左右摇摆
            if self._thinking:
                x += int(math.sin(self._anim_tick * 0.15) * 3)

            painter.drawPixmap(x, y, scaled)

            # 程序化眨眼效果（仅在非精灵模式下使用）
            if not self._sprite_animator and self._is_blinking:
                eye_y = y + int(target_h * 0.28)
                eye_lx = x + int(target_w * 0.40)
                eye_rx = x + int(target_w * 0.60)
                painter.setPen(QPen(QColor("#8B6FA8"), 2.5, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(eye_lx - 4, eye_y, eye_lx + 4, eye_y)
                painter.drawLine(eye_rx - 4, eye_y, eye_rx + 4, eye_y)

            # 绘制思考指示：头顶画省略号
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

        painter.end()
