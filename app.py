"""Tkinter application shell and non-blocking camera loop for Air_Board."""
from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
import os
import tempfile
import threading
import urllib.parse
import urllib.request

import cv2
from PIL import Image, ImageTk

from canvas_manager import CanvasManager
from hand_tracker import HandTracker
from image_manager import ImageManager
from media_manager import MediaManager


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
        self.output_photo: ImageTk.PhotoImage | None = None
        self.output_window: tk.Toplevel | None = None
        self.output_label: tk.Label | None = None
        self.live_controls: tk.Toplevel | None = None
        self.media_controls: tk.Toplevel | None = None
        self.presentation = False
        self.pen_bgr = (30, 30, 255)
        self.canvas = CanvasManager()
        self.images = ImageManager()
        self.media = MediaManager()
        try:
            self.tracker = HandTracker()
        except Exception as exc:
            raise RuntimeError(f"MediaPipe could not be initialized: {exc}") from exc

        self.camera_var = tk.StringVar(value="0")
        self.width_var = tk.IntVar(value=5)
        self.x_var = tk.IntVar(value=50)
        self.y_var = tk.IntVar(value=50)
        self.scale_var = tk.IntVar(value=45)
        self.media_x_var = tk.IntVar(value=50)
        self.media_y_var = tk.IntVar(value=50)
        self.media_scale_var = tk.IntVar(value=45)
        self.loop_var = tk.BooleanVar(value=True)
        self.mute_var = tk.BooleanVar(value=True)
        self.landmarks_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Camera stopped")
        self._build_ui()
        self._bind_shortcuts()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self) -> None:
        self.main_frame = tk.Frame(self.root, bg="#20242b")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.main_frame.grid_rowconfigure(0, weight=1)
        # The preview may grow, but it can never consume the fixed-width controls.
        self.main_frame.grid_columnconfigure(0, weight=1, minsize=640)
        self.main_frame.grid_columnconfigure(1, weight=0, minsize=300)
        self.preview_frame = tk.Frame(self.main_frame, bg="#111318", highlightthickness=1, highlightbackground="#4a5568")
        self.preview_frame.grid(row=0, column=0, sticky="nsew")
        # Ignore the incoming image's requested dimensions; the grid owns layout.
        self.preview_frame.grid_propagate(False)
        self.preview_label = tk.Label(self.preview_frame, bg="#111318", fg="#aeb8c5", text="Click Start Camera to begin", font=("Segoe UI", 15))
        self.preview_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.controls = tk.Frame(self.main_frame, bg="#2b3039", width=280)
        self.controls.grid(row=0, column=1, sticky="ns", padx=(12, 0))
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
        ttk.Button(self.controls, text="Add Local Video", command=self.add_local_video).pack(fill=tk.X, padx=14, pady=3)
        ttk.Button(self.controls, text="Add MP4 URL", command=self.add_mp4_url).pack(fill=tk.X, padx=14, pady=3)
        ttk.Button(self.controls, text="Video Controls", command=self.show_media_controls).pack(fill=tk.X, padx=14, pady=3)
        ttk.Button(self.controls, text="Remove Video", command=self.remove_media).pack(fill=tk.X, padx=14, pady=3)
        ttk.Separator(self.controls).pack(fill=tk.X, padx=14, pady=5)
        actions = tk.Frame(self.controls, bg="#2b3039")
        actions.pack(fill=tk.X, padx=14, pady=4)
        ttk.Button(actions, text="Undo", command=self.undo).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(actions, text="Clear Canvas", command=self.clear).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        tk.Checkbutton(self.controls, text="Show hand landmarks", variable=self.landmarks_var, bg="#2b3039", fg="#e8edf4", selectcolor="#3b4350", activebackground="#2b3039", activeforeground="#fff").pack(anchor=tk.W, padx=14, pady=4)
        ttk.Button(self.controls, text="Open OBS Output (F11)", command=self.toggle_presentation).pack(fill=tk.X, padx=14, pady=4)
        tk.Label(self.controls, textvariable=self.status_var, bg="#1d8254", fg="white", font=("Segoe UI", 10, "bold"), padx=8, pady=7).pack(fill=tk.X, padx=14, pady=(8, 8))
        self._label("C clear   Ctrl+Z undo   I image\nV local video   R remove image   Esc close", 8, "#b8c2d0").pack(pady=2)

    def _label(self, text: str, size: int, color: str = "#f3f6fb") -> tk.Label:
        return tk.Label(self.controls, text=text, bg="#2b3039", fg=color, font=("Segoe UI", size))

    def _slider(self, label: str, variable: tk.IntVar, minimum: int, maximum: int) -> None:
        self._label(label, 9, "#d6dce5").pack(anchor=tk.W, padx=14, pady=(5, 0))
        tk.Scale(self.controls, variable=variable, from_=minimum, to=maximum, orient=tk.HORIZONTAL, showvalue=True, bg="#2b3039", fg="#e8edf4", troughcolor="#454e5b", highlightthickness=0, activebackground="#3b82f6").pack(fill=tk.X, padx=12)

    def _bind_shortcuts(self) -> None:
        self.root.bind_all("<Key-c>", lambda e: self._shortcut(e, self.clear))
        self.root.bind_all("<Control-z>", lambda e: self._shortcut(e, self.undo))
        self.root.bind_all("<Key-i>", lambda e: self._shortcut(e, self.add_image))
        self.root.bind_all("<Key-v>", lambda e: self._shortcut(e, self.add_local_video))
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
        parent = self.live_controls if self.live_controls and self.live_controls.winfo_exists() else self.root
        chosen = colorchooser.askcolor(parent=parent, title="Choose pen colour")
        if chosen[0]:
            r, g, b = (int(value) for value in chosen[0])
            self.pen_bgr = (b, g, r)

    def set_pen_color(self, rgb: tuple[int, int, int]) -> None:
        r, g, b = rgb
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
        # Keep this composed frame natural for the clean OBS output window.
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
        frame = self.media.overlay(frame, self.media_x_var.get(), self.media_y_var.get(), self.media_scale_var.get())
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

    @staticmethod
    def _photo_for_frame(frame, max_width: int, max_height: int) -> ImageTk.PhotoImage:
        """Create a letterboxed 16:9 preview without changing its layout size."""
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        # Render inside a fixed 16:9 viewport. The source is letterboxed rather
        # than stretched, retaining its native proportions.
        target_width = min(max_width, int(max_height * 16 / 9))
        target_height = int(target_width * 9 / 16)
        image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        viewport = Image.new("RGB", (target_width, target_height), "#111318")
        viewport.paste(image, ((target_width - image.width) // 2, (target_height - image.height) // 2))
        return ImageTk.PhotoImage(image=viewport)

    def _show_frame(self, output_frame) -> None:
        # While OBS Output is open, only that dedicated window receives video.
        # The main window remains a lightweight controller for live settings.
        if not self.presentation:
            preview_frame = cv2.flip(output_frame, 1)
            max_width = max(320, self.preview_frame.winfo_width() - 4)
            max_height = max(240, self.preview_frame.winfo_height() - 4)
            self.preview_photo = self._photo_for_frame(preview_frame, max_width, max_height)
            self.preview_label.configure(image=self.preview_photo, text="")
        # OBS captures this separate window, which retains the natural orientation.
        if self.output_window and self.output_label and self.output_window.winfo_exists():
            width = max(320, self.output_window.winfo_width() - 4)
            height = max(240, self.output_window.winfo_height() - 4)
            self.output_photo = self._photo_for_frame(output_frame, width, height)
            self.output_label.configure(image=self.output_photo)

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

    def add_local_video(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root, title="Choose a local video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.webm"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.media.load(path)
            self._reset_media_settings()
            self.show_media_controls()
        except Exception as exc:
            messagebox.showerror("Video could not be loaded", f"Please choose a supported local video file.\n\n{exc}", parent=self.root)

    def add_mp4_url(self) -> None:
        url = simpledialog.askstring("Add MP4 URL", "Paste a direct MP4 URL:", parent=self.root)
        if not url:
            return
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.path.lower().endswith(".mp4"):
            messagebox.showerror("Invalid URL", "Enter a direct http or https URL ending in .mp4.", parent=self.root)
            return
        self.status_var.set("Downloading MP4 URL...")
        threading.Thread(target=self._download_mp4, args=(url,), daemon=True).start()

    def _download_mp4(self, url: str) -> None:
        file_descriptor, path = tempfile.mkstemp(prefix="air_board_", suffix=".mp4")
        os.close(file_descriptor)
        try:
            urllib.request.urlretrieve(url, path)
            self.root.after(0, lambda: self._finish_mp4_download(path))
        except Exception as exc:
            try:
                os.remove(path)
            except OSError:
                pass
            self.root.after(0, lambda: messagebox.showerror("MP4 download failed", str(exc), parent=self.root))

    def _finish_mp4_download(self, path: str) -> None:
        try:
            self.media.load(path, temporary=True)
            self._reset_media_settings()
            self.show_media_controls()
        except Exception as exc:
            try:
                os.remove(path)
            except OSError:
                pass
            messagebox.showerror("Video could not be loaded", str(exc), parent=self.root)

    def _reset_media_settings(self) -> None:
        self.media_x_var.set(50); self.media_y_var.set(50); self.media_scale_var.set(45)
        self.loop_var.set(True); self.mute_var.set(True)
        self.media.loop = True; self.media.muted = True

    def remove_media(self) -> None:
        self.media.remove()
        self._hide_media_controls()

    def show_media_controls(self) -> None:
        if not self.media.loaded:
            messagebox.showinfo("No video", "Add a local video or direct MP4 URL before opening its controls.", parent=self.root)
            return
        if self.media_controls and self.media_controls.winfo_exists():
            self.media_controls.deiconify()
            self.media_controls.lift()
            return
        self.media_controls = tk.Toplevel(self.root)
        self.media_controls.title(f"Air_Board – Video Controls: {self.media.name}")
        self.media_controls.configure(bg="#2b3039")
        self.media_controls.resizable(False, False)
        if self.presentation:
            self.media_controls.attributes("-topmost", True)
        tk.Label(self.media_controls, text="Video Controls", bg="#2b3039", fg="white", font=("Segoe UI", 13, "bold")).pack(pady=(12, 2))
        tk.Label(self.media_controls, text="Video audio is not sent to OBS", bg="#2b3039", fg="#b8c2d0", font=("Segoe UI", 8)).pack(pady=(0, 5))
        playback = tk.Frame(self.media_controls, bg="#2b3039")
        playback.pack(fill=tk.X, padx=14, pady=4)
        ttk.Button(playback, text="Play", command=self.media.play).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(playback, text="Pause", command=self.media.pause).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(playback, text="Restart", command=self.media.restart).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        options = tk.Frame(self.media_controls, bg="#2b3039")
        options.pack(fill=tk.X, padx=14, pady=2)
        tk.Checkbutton(options, text="Loop", variable=self.loop_var, command=self._set_loop, bg="#2b3039", fg="#e8edf4", selectcolor="#3b4350", activebackground="#2b3039", activeforeground="white").pack(side=tk.LEFT)
        tk.Checkbutton(options, text="Mute", variable=self.mute_var, command=self._set_mute, bg="#2b3039", fg="#e8edf4", selectcolor="#3b4350", activebackground="#2b3039", activeforeground="white").pack(side=tk.LEFT, padx=12)
        self.freeze_button = ttk.Button(options, text="Freeze Frame", command=self._toggle_freeze)
        self.freeze_button.pack(side=tk.RIGHT)
        self._media_slider("Horizontal position", self.media_x_var, 0, 100)
        self._media_slider("Vertical position", self.media_y_var, 0, 100)
        self._media_slider("Scale (%)", self.media_scale_var, 10, 150)
        ttk.Button(self.media_controls, text="Remove Video", command=self.remove_media).pack(fill=tk.X, padx=14, pady=(6, 12))
        self.media_controls.protocol("WM_DELETE_WINDOW", self._hide_media_controls)

    def _media_slider(self, label: str, variable: tk.IntVar, minimum: int, maximum: int) -> None:
        tk.Label(self.media_controls, text=label, bg="#2b3039", fg="#e8edf4", font=("Segoe UI", 9)).pack(anchor=tk.W, padx=14, pady=(4, 0))
        tk.Scale(self.media_controls, variable=variable, from_=minimum, to=maximum, orient=tk.HORIZONTAL, bg="#2b3039", fg="#e8edf4", troughcolor="#454e5b", highlightthickness=0, activebackground="#3b82f6").pack(fill=tk.X, padx=12)

    def _hide_media_controls(self) -> None:
        if self.media_controls and self.media_controls.winfo_exists():
            self.media_controls.destroy()
        self.media_controls = None

    def _set_loop(self) -> None:
        self.media.loop = self.loop_var.get()

    def _set_mute(self) -> None:
        self.media.muted = self.mute_var.get()

    def _toggle_freeze(self) -> None:
        self.media.toggle_freeze()
        if self.media_controls and self.media_controls.winfo_exists():
            self.freeze_button.configure(text="Unfreeze" if self.media.frozen else "Freeze Frame")

    def undo(self) -> None:
        self.canvas.undo()

    def clear(self) -> None:
        self.canvas.clear()

    def toggle_landmarks(self) -> None:
        self.landmarks_var.set(not self.landmarks_var.get())

    def toggle_presentation(self) -> None:
        self.presentation = not self.presentation
        if self.presentation:
            self._open_output_window()
        else:
            self._close_output_window()

    def _open_output_window(self) -> None:
        self.preview_photo = None
        self.preview_label.configure(image="", text="OBS Output is live\nUse this window for controls")
        self.output_window = tk.Toplevel(self.root)
        self.output_window.title("Air_Board – OBS Output")
        self.output_window.configure(bg="#111318")
        self.output_window.attributes("-fullscreen", True)
        self.output_label = tk.Label(self.output_window, bg="#111318")
        self.output_label.pack(fill=tk.BOTH, expand=True)
        self.output_window.bind("<Escape>", lambda _event: self.toggle_presentation())
        self.output_window.protocol("WM_DELETE_WINDOW", self.toggle_presentation)
        self._open_live_controls()

    def _open_live_controls(self) -> None:
        self.live_controls = tk.Toplevel(self.root)
        self.live_controls.title("Air_Board – Live Controls")
        self.live_controls.configure(bg="#2b3039")
        self.live_controls.attributes("-topmost", True)
        self.live_controls.resizable(False, False)
        self.live_controls.geometry("270x340+24+80")
        tk.Label(self.live_controls, text="Live Controls", bg="#2b3039", fg="white", font=("Segoe UI", 13, "bold")).pack(pady=(12, 3))
        tk.Label(self.live_controls, text="Not included in OBS Output", bg="#2b3039", fg="#b8c2d0", font=("Segoe UI", 8)).pack(pady=(0, 8))
        ttk.Button(self.live_controls, text="Choose Pen Colour", command=self.choose_color).pack(fill=tk.X, padx=14, pady=3)
        palette = tk.Frame(self.live_controls, bg="#2b3039")
        palette.pack(pady=4)
        for name, rgb in (("Red", (255, 40, 40)), ("Blue", (45, 110, 255)), ("Green", (30, 190, 90)), ("Yellow", (245, 205, 35)), ("White", (255, 255, 255))):
            tk.Button(palette, text=name[0], width=2, command=lambda value=rgb: self.set_pen_color(value), bg="#3b4350", fg="white", activebackground="#586476").pack(side=tk.LEFT, padx=2)
        tk.Label(self.live_controls, text="Stroke width", bg="#2b3039", fg="#e8edf4", font=("Segoe UI", 9)).pack(anchor=tk.W, padx=14, pady=(5, 0))
        tk.Scale(self.live_controls, variable=self.width_var, from_=1, to=25, orient=tk.HORIZONTAL, bg="#2b3039", fg="#e8edf4", troughcolor="#454e5b", highlightthickness=0, activebackground="#3b82f6").pack(fill=tk.X, padx=12)
        actions = tk.Frame(self.live_controls, bg="#2b3039")
        actions.pack(fill=tk.X, padx=14, pady=6)
        ttk.Button(actions, text="Undo", command=self.undo).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(actions, text="Clear", command=self.clear).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        ttk.Button(self.live_controls, text="Close OBS Output", command=self.toggle_presentation).pack(fill=tk.X, padx=14, pady=(1, 10))
        ttk.Button(self.live_controls, text="Video Controls", command=self.show_media_controls).pack(fill=tk.X, padx=14, pady=(0, 10))
        self.live_controls.protocol("WM_DELETE_WINDOW", self._hide_live_controls)

    def _hide_live_controls(self) -> None:
        if self.live_controls and self.live_controls.winfo_exists():
            self.live_controls.destroy()
        self.live_controls = None

    def _close_output_window(self) -> None:
        if self.output_window and self.output_window.winfo_exists():
            self.output_window.destroy()
        self.output_window = None
        self.output_label = None
        self.output_photo = None
        self.preview_label.configure(image="", text="Returning preview to main window...")
        if self.live_controls and self.live_controls.winfo_exists():
            self.live_controls.destroy()
        self.live_controls = None

    def on_escape(self, _event: tk.Event) -> str:
        if self.presentation:
            self.toggle_presentation()
        else:
            self.close()
        return "break"

    def close(self) -> None:
        self.presentation = False
        self._close_output_window()
        self._hide_media_controls()
        self.media.remove()
        self.stop_camera()
        self.tracker.close()
        self.root.destroy()
