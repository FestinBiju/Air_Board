"""Single local MP4/video overlay with playback controls for Air_Board."""
from __future__ import annotations

import os
import time

import cv2
import numpy as np


class MediaManager:
    def __init__(self) -> None:
        self.video: cv2.VideoCapture | None = None
        self.current: np.ndarray | None = None
        self.video_due = 0.0
        self.video_interval = 1 / 30
        self.name = ""
        self.loop = True
        self.muted = True  # Air_Board never sends or plays overlay audio.
        self.paused = False
        self.frozen = False
        self._temporary_path: str | None = None

    @property
    def loaded(self) -> bool:
        return self.video is not None

    def load(self, path: str, temporary: bool = False) -> None:
        self.remove()
        capture = cv2.VideoCapture(path)
        if not capture.isOpened():
            capture.release()
            raise ValueError("OpenCV could not open this video file.")
        fps = capture.get(cv2.CAP_PROP_FPS)
        self.video_interval = 1 / fps if fps and fps > 1 else 1 / 30
        self.video = capture
        self.current = None
        self.video_due = 0.0
        self.paused = False
        self.frozen = False
        self._temporary_path = path if temporary else None
        self.name = os.path.basename(path)

    def play(self) -> None:
        self.paused = False
        self.frozen = False
        self.video_due = 0.0

    def pause(self) -> None:
        self.paused = True

    def restart(self) -> None:
        if self.video is not None:
            self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.current = None
        self.video_due = 0.0
        self.play()

    def toggle_freeze(self) -> None:
        self.frozen = not self.frozen
        if not self.frozen:
            self.video_due = 0.0

    def remove(self) -> None:
        if self.video is not None:
            self.video.release()
        self.video = None
        self.current = None
        self.name = ""
        self.paused = False
        self.frozen = False
        if self._temporary_path:
            try:
                os.remove(self._temporary_path)
            except OSError:
                pass
        self._temporary_path = None

    def overlay(self, frame: np.ndarray, x_percent: int, y_percent: int, scale_percent: int) -> np.ndarray:
        source = self._next_frame()
        if source is None:
            return frame
        height, width = source.shape[:2]
        size = (max(1, int(width * scale_percent / 100)), max(1, int(height * scale_percent / 100)))
        media = cv2.resize(source, size, interpolation=cv2.INTER_AREA if scale_percent <= 100 else cv2.INTER_LINEAR)
        frame_height, frame_width = frame.shape[:2]
        media_height, media_width = media.shape[:2]
        x = int((frame_width - media_width) * x_percent / 100)
        y = int((frame_height - media_height) * y_percent / 100)
        left, top, right, bottom = max(0, x), max(0, y), min(frame_width, x + media_width), min(frame_height, y + media_height)
        if left >= right or top >= bottom:
            return frame
        frame[top:bottom, left:right] = media[top - y:bottom - y, left - x:right - x]
        return frame

    def _next_frame(self) -> np.ndarray | None:
        if self.video is None or self.paused or self.frozen:
            return self.current
        now = time.monotonic()
        if self.current is not None and now < self.video_due:
            return self.current
        ok, frame = self.video.read()
        if not ok and self.loop:
            self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.video.read()
        if not ok:
            self.paused = True
            return self.current
        self.current = frame
        self.video_due = now + self.video_interval
        return self.current
