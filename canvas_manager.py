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
    shape: str = "free"
    data: tuple[int, ...] = ()


class CanvasManager:
    def __init__(self) -> None:
        self.strokes: list[Stroke] = []
        self.active_stroke: Stroke | None = None

    def start_stroke(self, point: tuple[int, int], color: tuple[int, int, int], width: int) -> None:
        self.active_stroke = Stroke([point], color, width)

    def add_point(self, point: tuple[int, int]) -> None:
        if self.active_stroke is not None:
            self.active_stroke.points.append(point)

    def finish_stroke(self, smart_shapes: bool = False) -> None:
        if self.active_stroke and self.active_stroke.points:
            if smart_shapes:
                self._clean_shape(self.active_stroke)
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
        if stroke.shape == "line":
            cv2.line(frame, stroke.data[:2], stroke.data[2:], stroke.color, stroke.width, cv2.LINE_AA)
            return
        if stroke.shape == "arrow":
            cv2.arrowedLine(frame, stroke.data[:2], stroke.data[2:], stroke.color, stroke.width, cv2.LINE_AA, tipLength=0.18)
            return
        if stroke.shape == "circle":
            cv2.circle(frame, stroke.data[:2], stroke.data[2], stroke.color, stroke.width, cv2.LINE_AA)
            return
        if stroke.shape == "rectangle":
            cv2.rectangle(frame, stroke.data[:2], stroke.data[2:], stroke.color, stroke.width, cv2.LINE_AA)
            return
        if len(stroke.points) == 1:
            cv2.circle(frame, stroke.points[0], max(1, stroke.width // 2), stroke.color, -1, cv2.LINE_AA)
        for start, end in zip(stroke.points, stroke.points[1:]):
            cv2.line(frame, start, end, stroke.color, stroke.width, cv2.LINE_AA)

    @staticmethod
    def _clean_shape(stroke: Stroke) -> None:
        if len(stroke.points) < 5:
            return
        points = np.asarray(stroke.points, dtype=np.float32)
        start, end = points[0], points[-1]
        diagonal = float(np.linalg.norm(end - start))
        x0, y0 = points.min(axis=0).astype(int)
        x1, y1 = points.max(axis=0).astype(int)
        width, height = x1 - x0, y1 - y0
        if diagonal > 40:
            direction = end - start
            distances = np.abs(direction[0] * (start[1] - points[:, 1]) - (start[0] - points[:, 0]) * direction[1]) / diagonal
            if float(distances.max()) < max(8, diagonal * 0.10):
                stroke.shape, stroke.data = "line", (int(start[0]), int(start[1]), int(end[0]), int(end[1]))
                return
        closed = diagonal < max(20, (width + height) * 0.18)
        if closed and min(width, height) > 25:
            center = points.mean(axis=0)
            radii = np.linalg.norm(points - center, axis=1)
            if radii.std() < radii.mean() * 0.28:
                stroke.shape, stroke.data = "circle", (int(center[0]), int(center[1]), int(radii.mean()))
                return
            border_distance = np.minimum.reduce((np.abs(points[:, 0] - x0), np.abs(points[:, 0] - x1), np.abs(points[:, 1] - y0), np.abs(points[:, 1] - y1)))
            if float(border_distance.mean()) < min(width, height) * 0.16:
                stroke.shape, stroke.data = "rectangle", (int(x0), int(y0), int(x1), int(y1))
