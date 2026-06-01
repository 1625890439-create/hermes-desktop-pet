"""Hermes API 客户端 — 通过 API Server 获得完整 Agent 能力（流式输出）"""

import json
import logging
from typing import Optional

import httpx
from PyQt5.QtCore import QThread, pyqtSignal

from . import config

logger = logging.getLogger(__name__)


class StreamWorker(QThread):
    """流式请求 Hermes API Server（完整 Agent，支持工具调用和命令执行）。"""

    text_chunk = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, messages: list[dict], parent=None):
        super().__init__(parent)
        self.messages = messages
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        headers = {
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.MODEL_NAME,
            "messages": self.messages,
            "stream": True,
        }

        try:
            with httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
                with client.stream(
                    "POST",
                    config.API_ENDPOINT,
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if self._abort:
                            break

                        line = line.strip()
                        if not line:
                            continue
                        if line == "data: [DONE]":
                            break
                        if not line.startswith("data: "):
                            continue

                        try:
                            chunk = json.loads(line[6:])
                            choices = chunk.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            # 只处理文本内容（工具调用在 server 端处理完毕后统一返回文本）
                            content = delta.get("content")
                            if content:
                                self.text_chunk.emit(content)
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue

        except httpx.ConnectError:
            self.error.emit("无法连接到 Hermes 服务器，请确认服务已启动。")
        except httpx.TimeoutException:
            self.error.emit("请求超时，请稍后再试。")
        except httpx.HTTPStatusError as e:
            self.error.emit(f"服务器返回错误：{e.response.status_code}")
        except Exception as e:
            logger.exception("流式请求异常")
            self.error.emit(f"发生未知错误：{e}")
        finally:
            if not self._abort:
                self.finished.emit()


class ChatManager:
    """管理对话历史和 API 请求。"""

    def __init__(self):
        self.messages: list[dict] = [
            {"role": "system", "content": config.SYSTEM_PROMPT}
        ]
        self._worker: Optional[StreamWorker] = None

    def send_message(self, user_text: str) -> StreamWorker:
        self.messages.append({"role": "user", "content": user_text})

        # 限制历史长度
        if len(self.messages) > config.MAX_HISTORY_LENGTH + 1:
            self.messages = [self.messages[0]] + self.messages[-(config.MAX_HISTORY_LENGTH):]

        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(2000)

        self._worker = StreamWorker(self.messages)
        return self._worker

    def append_assistant_reply(self, reply: str):
        self.messages.append({"role": "assistant", "content": reply})

    def clear_history(self):
        self.messages = [self.messages[0]]
