"""MediaPipe hand tracking and pinch-state hysteresis."""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class HandResult:
    point: tuple[int, int] | None
    drawing: bool
    landmarks: object | None
    clear_gesture: bool = False


class HandTracker:
    PINCH_START_THRESHOLD = 40
    PINCH_RELEASE_THRESHOLD = 55

    def __init__(self, smoothing: float = 0.4) -> None:
        self.smoothing = smoothing
        self.mp_hands = mp.solutions.hands
        self.drawer = mp.solutions.drawing_utils
        self.connections = self.mp_hands.HAND_CONNECTIONS
        self.hands = self.mp_hands.Hands(
            static_image_mode=False, max_num_hands=1, model_complexity=0,
            min_detection_confidence=0.6, min_tracking_confidence=0.6,
        )
        self.drawing = False
        self.smoothed: tuple[float, float] | None = None
        self.missing_frames = 0

    def process(self, frame: np.ndarray, detect_fist: bool = False) -> HandResult:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)
        if not result.multi_hand_landmarks:
            self.missing_frames += 1
            if self.missing_frames > 4:
                self.drawing = False
                self.smoothed = None
            return HandResult(None, self.drawing, None)

        self.missing_frames = 0
        landmarks = result.multi_hand_landmarks[0]
        height, width = frame.shape[:2]
        index = landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        thumb = landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        raw_x, raw_y = int(index.x * width), int(index.y * height)
        if self.smoothed is None:
            self.smoothed = (raw_x, raw_y)
        else:
            old_x, old_y = self.smoothed
            self.smoothed = (self.smoothing * raw_x + (1 - self.smoothing) * old_x,
                             self.smoothing * raw_y + (1 - self.smoothing) * old_y)
        point = (int(self.smoothed[0]), int(self.smoothed[1]))
        # A fist has at least three fingertips folded back toward the wrist.
        # Normalizing against each finger's PIP distance makes this independent
        # of how close the hand is to the camera.
        clear_gesture = detect_fist and self._is_closed_fist(landmarks)
        if clear_gesture:
            self.drawing = False
            return HandResult(point, False, landmarks, clear_gesture=True)
        distance = math.hypot((index.x - thumb.x) * width, (index.y - thumb.y) * height)
        if not self.drawing and distance < self.PINCH_START_THRESHOLD:
            self.drawing = True
        elif self.drawing and distance > self.PINCH_RELEASE_THRESHOLD:
            self.drawing = False
        return HandResult(point, self.drawing, landmarks)

    @staticmethod
    def _is_closed_fist(landmarks: object) -> bool:
        """Return true when at least three fingers are curled toward the wrist."""
        wrist = landmarks.landmark[0]
        curled_fingers = 0
        for tip_id, pip_id in ((8, 6), (12, 10), (16, 14), (20, 18)):
            tip = landmarks.landmark[tip_id]
            pip = landmarks.landmark[pip_id]
            tip_distance = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
            pip_distance = math.hypot(pip.x - wrist.x, pip.y - wrist.y)
            if tip_distance < pip_distance * 1.15:
                curled_fingers += 1
        return curled_fingers >= 3

    def draw_landmarks(self, frame: np.ndarray, landmarks: object) -> None:
        self.drawer.draw_landmarks(frame, landmarks, self.connections)

    def close(self) -> None:
        self.hands.close()
