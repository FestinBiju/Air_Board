"""Persistent air-drawing stroke storage and rendering."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Stroke:
    points: list[tuple[int, int]]
    color: tuple[int, int, int]  # BGR
    width: int


class CanvasManager:
    def __init__(self) -> None:
        self.strokes: list[Stroke] = []
        self.active_stroke: Stroke | None = None

    def start_stroke(self, point: tuple[int, int], color: tuple[int, int, int], width: int) -> None:
        self.active_stroke = Stroke([point], color, width)

    def add_point(self, point: tuple[int, int]) -> None:
        if self.active_stroke is not None:
            self.active_stroke.points.append(point)

    def finish_stroke(self) -> None:
        if self.active_stroke and self.active_stroke.points:
            self.strokes.append(self.active_stroke)
        self.active_stroke = None

    def cancel_active_stroke(self) -> None:
        self.active_stroke = None

    def undo(self) -> None:
        self.cancel_active_stroke()
        if self.strokes:
            self.strokes.pop()

    def clear(self) -> None:
        self.strokes.clear()
        self.cancel_active_stroke()

    def render(self, frame: np.ndarray) -> np.ndarray:
        for stroke in [*self.strokes, *([self.active_stroke] if self.active_stroke else [])]:
            self._render_stroke(frame, stroke)
        return frame

    @staticmethod
    def _render_stroke(frame: np.ndarray, stroke: Stroke) -> None:
        if len(stroke.points) == 1:
            cv2.circle(frame, stroke.points[0], max(1, stroke.width // 2), stroke.color, -1, cv2.LINE_AA)
        for start, end in zip(stroke.points, stroke.points[1:]):
            cv2.line(frame, start, end, stroke.color, stroke.width, cv2.LINE_AA)
