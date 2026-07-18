"""Tkinter application shell and non-blocking camera loop for Air_Board."""
from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from canvas_manager import CanvasManager
from hand_tracker import HandTracker
from image_manager import ImageManager


class AirBoardApp:
    FRAME_DELAY_MS = 33

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Air_Board – Gesture Drawing Camera")
        root.minsize(1050, 650)
        root.configure(bg="#20242b")
        self.capture: cv2.VideoCapture | None = None
        self.after_id: str | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.presentation = False
        self.pen_bgr = (30, 30, 255)
        self.canvas = CanvasManager()
        self.images = ImageManager()
        try:
            self.tracker = HandTracker()
        except Exception as exc:
            raise RuntimeError(f"MediaPipe could not be initialized: {exc}") from exc

        self.camera_var = tk.StringVar(value="0")
        self.width_var = tk.IntVar(value=5)
        self.x_var = tk.IntVar(value=50)
        self.y_var = tk.IntVar(value=50)
        self.scale_var = tk.IntVar(value=45)
        self.landmarks_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Camera stopped")
        self._build_ui()
        self._bind_shortcuts()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self) -> None:
        self.main_frame = tk.Frame(self.root, bg="#20242b")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.preview_frame = tk.Frame(self.main_frame, bg="#111318", highlightthickness=1, highlightbackground="#4a5568")
        self.preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.preview_label = tk.Label(self.preview_frame, bg="#111318", fg="#aeb8c5", text="Click Start Camera to begin", font=("Segoe UI", 15))
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        self.controls = tk.Frame(self.main_frame, bg="#2b3039", width=280)
        self.controls.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        self.controls.pack_propagate(False)
        self._label("Air_Board", 18).pack(pady=(14, 2))
        self._label("Gesture Drawing Camera", 10, "#b8c2d0").pack(pady=(0, 12))
        camera_row = tk.Frame(self.controls, bg="#2b3039")
        camera_row.pack(fill=tk.X, padx=14, pady=3)
        self._label("Camera", 10).pack(in_=camera_row, side=tk.LEFT)
        ttk.Combobox(camera_row, textvariable=self.camera_var, values=("0", "1", "2", "3"), width=4, state="readonly").pack(side=tk.RIGHT)
        buttons = tk.Frame(self.controls, bg="#2b3039")
        buttons.pack(fill=tk.X, padx=14, pady=6)
        self.start_button = ttk.Button(buttons, text="Start Camera", command=self.start_camera)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(buttons, text="Stop", command=self.stop_camera).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        ttk.Separator(self.controls).pack(fill=tk.X, padx=14, pady=5)
        ttk.Button(self.controls, text="Choose Pen Colour", command=self.choose_color).pack(fill=tk.X, padx=14, pady=4)
        self._slider("Stroke width", self.width_var, 1, 25)
        ttk.Separator(self.controls).pack(fill=tk.X, padx=14, pady=5)
        ttk.Button(self.controls, text="Add / Replace Image", command=self.add_image).pack(fill=tk.X, padx=14, pady=3)
        ttk.Button(self.controls, text="Remove Image", command=self.remove_image).pack(fill=tk.X, padx=14, pady=3)
        self._slider("Image X position", self.x_var, 0, 100)
        self._slider("Image Y position", self.y_var, 0, 100)
        self._slider("Image scale (%)", self.scale_var, 20, 150)
        ttk.Separator(self.controls).pack(fill=tk.X, padx=14, pady=5)
        actions = tk.Frame(self.controls, bg="#2b3039")
        actions.pack(fill=tk.X, padx=14, pady=4)
        ttk.Button(actions, text="Undo", command=self.undo).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(actions, text="Clear Canvas", command=self.clear).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        tk.Checkbutton(self.controls, text="Show hand landmarks", variable=self.landmarks_var, bg="#2b3039", fg="#e8edf4", selectcolor="#3b4350", activebackground="#2b3039", activeforeground="#fff").pack(anchor=tk.W, padx=14, pady=4)
        ttk.Button(self.controls, text="Presentation Mode (F11)", command=self.toggle_presentation).pack(fill=tk.X, padx=14, pady=4)
        tk.Label(self.controls, textvariable=self.status_var, bg="#1d8254", fg="white", font=("Segoe UI", 10, "bold"), padx=8, pady=7).pack(fill=tk.X, padx=14, pady=(8, 8))
        self._label("C clear   Ctrl+Z undo   I image\nR remove   L landmarks   Esc close", 8, "#b8c2d0").pack(pady=2)

    def _label(self, text: str, size: int, color: str = "#f3f6fb") -> tk.Label:
        return tk.Label(self.controls, text=text, bg="#2b3039", fg=color, font=("Segoe UI", size))

    def _slider(self, label: str, variable: tk.IntVar, minimum: int, maximum: int) -> None:
        self._label(label, 9, "#d6dce5").pack(anchor=tk.W, padx=14, pady=(5, 0))
        tk.Scale(self.controls, variable=variable, from_=minimum, to=maximum, orient=tk.HORIZONTAL, showvalue=True, bg="#2b3039", fg="#e8edf4", troughcolor="#454e5b", highlightthickness=0, activebackground="#3b82f6").pack(fill=tk.X, padx=12)

    def _bind_shortcuts(self) -> None:
        self.root.bind_all("<Key-c>", lambda e: self._shortcut(e, self.clear))
        self.root.bind_all("<Control-z>", lambda e: self._shortcut(e, self.undo))
        self.root.bind_all("<Key-i>", lambda e: self._shortcut(e, self.add_image))
        self.root.bind_all("<Key-r>", lambda e: self._shortcut(e, self.remove_image))
        self.root.bind_all("<Key-l>", lambda e: self._shortcut(e, self.toggle_landmarks))
        self.root.bind_all("<F11>", lambda e: self.toggle_presentation())
        self.root.bind_all("<Escape>", self.on_escape)

    @staticmethod
    def _typing(widget: tk.Widget) -> bool:
        return isinstance(widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox))

    def _shortcut(self, event: tk.Event, callback: object) -> str | None:
        if not self._typing(event.widget):
            callback()  # type: ignore[operator]
            return "break"
        return None

    def choose_color(self) -> None:
        chosen = colorchooser.askcolor(parent=self.root, title="Choose pen colour")
        if chosen[0]:
            r, g, b = (int(value) for value in chosen[0])
            self.pen_bgr = (b, g, r)

    def start_camera(self) -> None:
        if self.capture is not None:
            return
        index = int(self.camera_var.get())
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(index)
        if not capture.isOpened():
            messagebox.showerror("Camera unavailable", f"Could not open camera {index}. Check that it is connected and not in use.", parent=self.root)
            return
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.capture = capture
        self.start_button.configure(state=tk.DISABLED)
        self.status_var.set("Looking for hand")
        self.update_frame()

    def stop_camera(self) -> None:
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.capture:
            self.capture.release()
            self.capture = None
        self.canvas.finish_stroke()
        self.tracker.drawing = False
        self.status_var.set("Camera stopped")
        self.start_button.configure(state=tk.NORMAL)

    def update_frame(self) -> None:
        if not self.capture:
            return
        ok, frame = self.capture.read()
        if not ok:
            self.status_var.set("Camera frame unavailable")
            self.after_id = self.root.after(250, self.update_frame)
            return
        frame = cv2.flip(frame, 1)
        clean_frame = frame.copy()
        result = self.tracker.process(clean_frame)
        if result.point is None:
            self.canvas.finish_stroke()
            self.status_var.set("No hand detected")
        elif result.drawing:
            if self.canvas.active_stroke is None:
                self.canvas.start_stroke(result.point, self.pen_bgr, self.width_var.get())
            else:
                self.canvas.add_point(result.point)
            self.status_var.set("Drawing")
        else:
            self.canvas.finish_stroke()
            self.status_var.set("Tracking")
        frame = self.images.overlay(frame, self.x_var.get(), self.y_var.get(), self.scale_var.get())
        self.canvas.render(frame)
        if self.landmarks_var.get() and result.landmarks:
            self.tracker.draw_landmarks(frame, result.landmarks)
        if result.point:
            cv2.circle(frame, result.point, 9, (0, 0, 255) if result.drawing else (0, 220, 0), -1, cv2.LINE_AA)
            cv2.circle(frame, result.point, 11, (255, 255, 255), 1, cv2.LINE_AA)
        if not self.presentation:
            cv2.putText(frame, self.status_var.get(), (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        self._show_frame(frame)
        self.after_id = self.root.after(self.FRAME_DELAY_MS, self.update_frame)

    def _show_frame(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        max_width = max(320, self.preview_frame.winfo_width() - 4)
        max_height = max(240, self.preview_frame.winfo_height() - 4)
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(image=image)
        self.preview_label.configure(image=self.preview_photo, text="")

    def add_image(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Choose an image", filetypes=[("Images", "*.png *.jpg *.jpeg"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.images.load(path)
            self.x_var.set(50); self.y_var.set(50)
        except Exception as exc:
            messagebox.showerror("Image could not be loaded", f"Please choose a valid PNG, JPG, or JPEG.\n\n{exc}", parent=self.root)

    def remove_image(self) -> None:
        self.images.remove()

    def undo(self) -> None:
        self.canvas.undo()

    def clear(self) -> None:
        self.canvas.clear()

    def toggle_landmarks(self) -> None:
        self.landmarks_var.set(not self.landmarks_var.get())

    def toggle_presentation(self) -> None:
        self.presentation = not self.presentation
        if self.presentation:
            self.controls.pack_forget()
            self.root.attributes("-fullscreen", True)
        else:
            self.root.attributes("-fullscreen", False)
            self.controls.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))

    def on_escape(self, _event: tk.Event) -> str:
        if self.presentation:
            self.toggle_presentation()
        else:
            self.close()
        return "break"

    def close(self) -> None:
        self.stop_camera()
        self.tracker.close()
        self.root.destroy()
