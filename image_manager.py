"""Image loading, cached resizing, clipping, and alpha compositing."""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


class ImageManager:
    def __init__(self) -> None:
        self.original: np.ndarray | None = None
        self._cached: np.ndarray | None = None
        self._cached_scale: int | None = None

    @property
    def loaded(self) -> bool:
        return self.original is not None

    def load(self, path: str) -> None:
        with Image.open(path) as image:
            rgba = image.convert("RGBA")
            array = np.asarray(rgba)
        self.original = cv2.cvtColor(array, cv2.COLOR_RGBA2BGRA)
        self._cached = None
        self._cached_scale = None

    def remove(self) -> None:
        self.original = None
        self._cached = None
        self._cached_scale = None

    def overlay(self, frame: np.ndarray, x_percent: int, y_percent: int, scale_percent: int) -> np.ndarray:
        if self.original is None:
            return frame
        if self._cached is None or self._cached_scale != scale_percent:
            height, width = self.original.shape[:2]
            size = (max(1, int(width * scale_percent / 100)), max(1, int(height * scale_percent / 100)))
            self._cached = cv2.resize(self.original, size, interpolation=cv2.INTER_AREA if scale_percent <= 100 else cv2.INTER_LINEAR)
            self._cached_scale = scale_percent
        image = self._cached
        fh, fw = frame.shape[:2]
        ih, iw = image.shape[:2]
        x = int((fw - iw) * x_percent / 100)
        y = int((fh - ih) * y_percent / 100)
        left, top, right, bottom = max(0, x), max(0, y), min(fw, x + iw), min(fh, y + ih)
        if left >= right or top >= bottom:
            return frame
        source = image[top - y:bottom - y, left - x:right - x]
        destination = frame[top:bottom, left:right]
        alpha = source[:, :, 3:4].astype(np.float32) / 255.0
        destination[:] = (source[:, :, :3].astype(np.float32) * alpha + destination.astype(np.float32) * (1 - alpha)).astype(np.uint8)
        return frame
