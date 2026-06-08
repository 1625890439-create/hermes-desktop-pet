"""精灵动画引擎 — 状态机动画播放与管理

状态机设计：
- idle:         默认站立，静止不动，30秒后自动触发随机 special
- special:      显示一个特殊动作帧，5秒后返回 idle
- jump_rising:  跳跃上升（拖拽中），播放前2帧，形象上移
- jump_landing: 跳跃落地（松开后），播放后4帧，播完回 idle
- talk_first:   收到指令，显示讲话第一帧
- talk_last:    遇到难题，显示讲话最后一帧
- special_6:    问题解决，显示特殊动作第6帧
- run:          跑步，循环播放所有帧
- blink:        眨眼/表情，循环播放所有帧
"""

import os
import json
import random
import logging
from typing import Optional
from enum import Enum

from PyQt5.QtGui import QPixmap

logger = logging.getLogger(__name__)


class PetState(Enum):
    IDLE = "idle"
    SPECIAL = "special"
    JUMP_RISING = "jump_rising"
    JUMP_LANDING = "jump_landing"
    TALK_FIRST = "talk_first"
    TALK_LAST = "talk_last"
    SPECIAL_6 = "special_6"
    RUN = "run"
    BLINK = "blink"
    # CodeNoNo 新增状态
    WAVING = "waving"
    FAILED = "failed"
    WAITING = "waiting"
    REVIEW = "review"
    RUN_LEFT = "run_left"
    RUN_RIGHT = "run_right"


class SpriteAnimator:
    """精灵动画引擎"""

    FRAME_DURATION = 5.0          # 普通帧持续时间（秒）
    JUMP_RISING_FRAME_DURATION = 0.3
    JUMP_LANDING_FRAME_DURATION = 0.4
    IDLE_TIMEOUT = 30.0           # idle 超时触发 special
    JUMP_RISING_FRAMES = 2

    # 循环动画帧持续时间
    RUN_FRAME_DURATION = 0.5
    BLINK_FRAME_DURATION = 0.8

    # CodeNoNo 一次性动画帧持续时间
    ONE_SHOT_FRAME_DURATION = 0.5  # waving/failed/waiting/review 共用
    RUN_SIDE_FRAME_DURATION = 0.4  # run-left/run-right

    # 眨眼循环次数（播完后回 idle）
    BLINK_LOOP_CYCLES = 1

    def __init__(self, sprite_dir: str):
        self._sprite_dir = sprite_dir
        self._frames: dict[str, list[QPixmap]] = {}

        self._state: PetState = PetState.IDLE
        self._current_frame_index: int = 0
        self._frame_timer: float = 0.0
        self._idle_timer: float = 0.0
        self._blink_loop_count: int = 0  # 眨眼循环计数
        self._next_blink_time: float = random.uniform(5.0, 15.0)  # 下次眨眼时间

        self._load()
        self._enter_state(PetState.IDLE)

    def _load(self):
        actions_path = os.path.join(self._sprite_dir, "actions.json")
        if not os.path.exists(actions_path):
            return
        try:
            with open(actions_path, "r", encoding="utf-8") as f:
                actions = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        for action_name, action_config in actions.items():
            action_dir = os.path.join(self._sprite_dir, action_name)
            if not os.path.isdir(action_dir):
                continue
            frames = []
            for filename in action_config.get("frames", []):
                frame_path = os.path.join(action_dir, filename)
                if os.path.exists(frame_path):
                    pixmap = QPixmap(frame_path)
                    if not pixmap.isNull():
                        frames.append(pixmap)
            if frames:
                self._frames[action_name] = frames

    # ── 属性 ──

    @property
    def is_loaded(self) -> bool:
        return len(self._frames) > 0

    @property
    def state(self) -> PetState:
        return self._state

    @property
    def available_actions(self) -> list[str]:
        return list(self._frames.keys())

    @property
    def is_jumping(self) -> bool:
        return self._state in (PetState.JUMP_RISING, PetState.JUMP_LANDING)

    # ── 帧获取 ──

    def current_frame(self) -> Optional[QPixmap]:
        action, idx = self._get_frame_source()
        if action not in self._frames:
            return None
        frames = self._frames[action]
        if not frames:
            return None
        return frames[min(idx, len(frames) - 1)]

    def _get_frame_source(self) -> tuple[str, int]:
        if self._state == PetState.IDLE:
            return "idle", 0
        elif self._state == PetState.SPECIAL:
            return "special", self._current_frame_index
        elif self._state in (PetState.JUMP_RISING, PetState.JUMP_LANDING):
            return "jump", self._current_frame_index
        elif self._state == PetState.TALK_FIRST:
            return "talk", 0
        elif self._state == PetState.TALK_LAST:
            return "talk", max(0, len(self._frames.get("talk", [])) - 1)
        elif self._state == PetState.SPECIAL_6:
            return "special", 5
        elif self._state == PetState.RUN:
            return "run", self._current_frame_index
        elif self._state == PetState.BLINK:
            return "blink", self._current_frame_index
        # CodeNoNo 新状态
        elif self._state == PetState.WAVING:
            return "waving", self._current_frame_index
        elif self._state == PetState.FAILED:
            return "failed", self._current_frame_index
        elif self._state == PetState.WAITING:
            return "waiting", self._current_frame_index
        elif self._state == PetState.REVIEW:
            return "review", self._current_frame_index
        elif self._state == PetState.RUN_LEFT:
            return "running-left", self._current_frame_index
        elif self._state == PetState.RUN_RIGHT:
            return "running-right", self._current_frame_index
        return "idle", 0

    def get_idle_frame(self) -> Optional[QPixmap]:
        if 'idle' in self._frames and self._frames['idle']:
            return self._frames['idle'][0]
        for frames in self._frames.values():
            if frames:
                return frames[0]
        return None

    # ── 状态切换 ──

    def _enter_state(self, state: PetState, frame_index: int = 0):
        self._state = state
        self._current_frame_index = frame_index
        self._frame_timer = 0.0
        if state == PetState.IDLE:
            self._idle_timer = 0.0
            self._next_blink_time = random.uniform(5.0, 15.0)

    def set_idle(self):
        self._enter_state(PetState.IDLE)

    def set_special_6(self):
        if 'special' in self._frames and len(self._frames['special']) >= 6:
            self._enter_state(PetState.SPECIAL_6, 5)

    def set_talk_first(self):
        if 'talk' in self._frames and self._frames['talk']:
            self._enter_state(PetState.TALK_FIRST, 0)

    def set_talk_last(self):
        if 'talk' in self._frames and self._frames['talk']:
            self._enter_state(PetState.TALK_LAST, len(self._frames['talk']) - 1)

    def start_jump(self):
        if 'jump' not in self._frames or len(self._frames['jump']) < 2:
            return
        self._enter_state(PetState.JUMP_RISING, 0)

    def release_jump(self):
        if self._state == PetState.JUMP_RISING:
            landing_start = min(self.JUMP_RISING_FRAMES, len(self._frames.get("jump", [])) - 1)
            self._enter_state(PetState.JUMP_LANDING, landing_start)

    def start_run(self):
        """开始跑步（循环播放所有 run 帧）"""
        if 'run' in self._frames and self._frames['run']:
            self._enter_state(PetState.RUN, 0)

    def stop_run(self):
        """停止跑步，回到 idle"""
        if self._state == PetState.RUN:
            self._enter_state(PetState.IDLE)

    def start_blink(self):
        """开始眨眼/表情动画（循环播放所有 blink 帧）"""
        if 'blink' in self._frames and self._frames['blink']:
            self._enter_state(PetState.BLINK, 0)

    def stop_blink(self):
        """停止眨眼，回到 idle"""
        if self._state == PetState.BLINK:
            self._enter_state(PetState.IDLE)

    # ── 帧更新 ──

    def update(self, dt: float):
        if self._state == PetState.IDLE:
            self._idle_timer += dt
            # 30秒超时触发 special
            if self._idle_timer >= self.IDLE_TIMEOUT:
                self._trigger_random_special()
            # 随机眨眼
            self._next_blink_time -= dt
            if self._next_blink_time <= 0:
                self._trigger_random_blink()

        elif self._state == PetState.SPECIAL:
            self._frame_timer += dt
            if self._frame_timer >= self.FRAME_DURATION:
                self._enter_state(PetState.IDLE)

        elif self._state == PetState.JUMP_RISING:
            self._frame_timer += dt
            if self._frame_timer >= self.JUMP_RISING_FRAME_DURATION:
                self._frame_timer -= self.JUMP_RISING_FRAME_DURATION
                self._current_frame_index += 1
                if self._current_frame_index >= self.JUMP_RISING_FRAMES:
                    self._current_frame_index = self.JUMP_RISING_FRAMES - 1

        elif self._state == PetState.JUMP_LANDING:
            self._frame_timer += dt
            if self._frame_timer >= self.JUMP_LANDING_FRAME_DURATION:
                self._frame_timer -= self.JUMP_LANDING_FRAME_DURATION
                self._current_frame_index += 1
                if self._current_frame_index >= len(self._frames.get("jump", [])):
                    self._enter_state(PetState.IDLE)

        elif self._state == PetState.RUN:
            # 跑步：循环播放所有帧
            self._frame_timer += dt
            if self._frame_timer >= self.RUN_FRAME_DURATION:
                self._frame_timer -= self.RUN_FRAME_DURATION
                run_frames = self._frames.get("run", [])
                self._current_frame_index = (self._current_frame_index + 1) % max(len(run_frames), 1)

        elif self._state == PetState.BLINK:
            # 眨眼：循环播放，播完指定圈数后回 idle
            self._frame_timer += dt
            if self._frame_timer >= self.BLINK_FRAME_DURATION:
                self._frame_timer -= self.BLINK_FRAME_DURATION
                blink_frames = self._frames.get("blink", [])
                self._current_frame_index += 1
                if self._current_frame_index >= len(blink_frames):
                    # 一圈播完
                    self._current_frame_index = 0
                    self._blink_loop_count += 1
                    if self._blink_loop_count >= self.BLINK_LOOP_CYCLES:
                        # 循环次数够了，回 idle
                        self._enter_state(PetState.IDLE)

        # CodeNoNo 一次性动画：waving/failed/waiting/review
        elif self._state in (PetState.WAVING, PetState.FAILED, PetState.WAITING, PetState.REVIEW):
            self._frame_timer += dt
            if self._frame_timer >= self.ONE_SHOT_FRAME_DURATION:
                self._frame_timer -= self.ONE_SHOT_FRAME_DURATION
                frames = self._frames.get(self._state.value.replace("run_left", "running-left").replace("run_right", "running-right"), [])
                if not frames:
                    frames_map = {
                        PetState.WAVING: self._frames.get("waving", []),
                        PetState.FAILED: self._frames.get("failed", []),
                        PetState.WAITING: self._frames.get("waiting", []),
                        PetState.REVIEW: self._frames.get("review", []),
                    }
                    frames = frames_map.get(self._state, [])
                self._current_frame_index += 1
                if self._current_frame_index >= len(frames):
                    self._enter_state(PetState.IDLE)

        # CodeNoNo 侧向跑：循环播放
        elif self._state in (PetState.RUN_LEFT, PetState.RUN_RIGHT):
            self._frame_timer += dt
            if self._frame_timer >= self.RUN_SIDE_FRAME_DURATION:
                self._frame_timer -= self.RUN_SIDE_FRAME_DURATION
                key = "running-left" if self._state == PetState.RUN_LEFT else "running-right"
                frames = self._frames.get(key, [])
                self._current_frame_index = (self._current_frame_index + 1) % max(len(frames), 1)

        # TALK_FIRST, TALK_LAST, SPECIAL_6 静态帧

    def _trigger_random_special(self):
        special_frames = self._frames.get("special", [])
        if not special_frames:
            self._enter_state(PetState.IDLE)
            return
        idx = random.randint(0, len(special_frames) - 1)
        self._enter_state(PetState.SPECIAL, idx)

    def _trigger_random_blink(self):
        """随机触发眨眼循环"""
        if 'blink' not in self._frames or not self._frames['blink']:
            self._next_blink_time = random.uniform(5.0, 15.0)
            return
        self._blink_loop_count = 0
        self._enter_state(PetState.BLINK, 0)
        self._next_blink_time = random.uniform(5.0, 15.0)  # 预设下次眨眼时间

    # ── CodeNoNo 状态触发 ──

    def start_waving(self):
        """挥手动作（一圈后回 idle）"""
        if 'waving' in self._frames and self._frames['waving']:
            self._enter_state(PetState.WAVING, 0)

    def start_failed(self):
        """失败动作（一圈后回 idle）"""
        if 'failed' in self._frames and self._frames['failed']:
            self._enter_state(PetState.FAILED, 0)

    def start_waiting(self):
        """等待动作（一圈后回 idle）"""
        if 'waiting' in self._frames and self._frames['waiting']:
            self._enter_state(PetState.WAITING, 0)

    def start_review(self):
        """审核动作（一圈后回 idle）"""
        if 'review' in self._frames and self._frames['review']:
            self._enter_state(PetState.REVIEW, 0)

    def start_run_left(self):
        """向左跑（循环）"""
        if 'running-left' in self._frames and self._frames['running-left']:
            self._enter_state(PetState.RUN_LEFT, 0)

    def start_run_right(self):
        """向右跑（循环）"""
        if 'running-right' in self._frames and self._frames['running-right']:
            self._enter_state(PetState.RUN_RIGHT, 0)

    def stop_run_side(self):
        """停止侧向跑，回到 idle"""
        if self._state in (PetState.RUN_LEFT, PetState.RUN_RIGHT):
            self._enter_state(PetState.IDLE)
