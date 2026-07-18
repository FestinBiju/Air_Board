# Air_Board

Air_Board is a lightweight Windows desktop prototype for drawing in the air over a live webcam feed. It is designed for capture with OBS Window Capture; it does not create a virtual camera itself.

## Features

- Aspect-ratio-locked 16:9 presenter preview with one-hand MediaPipe tracking
- Mirrored local presenter preview plus a natural-orientation OBS Output window
- Green index-finger cursor; red cursor while pinching to draw
- Persistent, anti-aliased strokes with clear and undo
- Live pen-colour and 1–25 px stroke-width controls
- One PNG/JPG/JPEG overlay with live X/Y position and scale controls
- PNG alpha support; annotations render above the overlay
- One local or direct-URL MP4 video overlay with playback and transform controls
- Optional landmarks and full-screen presentation mode for OBS

## Requirements and installation

Python 3.11 is recommended. From this folder on Windows:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Click **Start Camera**, raise one hand, and use the index fingertip as the cursor. Pinch the thumb and index fingertip together to begin a stroke; separate them to finish it.

Fist clearing is disabled by default because hand poses can vary. Enable **Enable fist clear (experimental)** to clear with a closed fist; each fist gesture clears only once until you open your hand again.

## Controls

- `C`: clear drawings
- `Ctrl+Z`: undo last completed stroke
- `I`: add or replace image
- `R`: remove image
- `L`: toggle landmarks
- `F11`: presentation mode
- `Escape`: leave presentation mode, or close the app normally

Use **Choose Pen Colour** and **Stroke width** before beginning a new stroke. Existing strokes retain their own settings. Add an image and adjust its X, Y, and scale sliders; drawing is always composited over it.

## Video overlay

Click **Add Local Video** (or press `V`) to choose an MP4, AVI, MOV, MKV, or WebM file. Use **Add MP4 URL** for a direct `https://.../file.mp4` link; Air_Board downloads it without blocking the webcam UI. **Video Controls** provides play, pause, restart, loop, mute, freeze frame, X/Y position, scale, and removal. Only one video overlay is active, and it is composed before the drawing canvas so annotations always appear over it.

The overlay never includes audio in the OBS Window Capture video feed; the mute control records the desired state while keeping that behavior explicit. Video decoding depends on the codecs installed with OpenCV; MP4 with H.264 is the most reliable option.

## OBS setup

Open OBS Studio, add a Window Capture source, select the Air_Board window, click Start Virtual Camera, and choose OBS Virtual Camera in your meeting app.

For a clean capture, press `F11` to open **Air_Board – OBS Output**. Capture that window in OBS; it is unmirrored for your audience while the main Air_Board window remains mirrored for comfortable air drawing. A separate always-on-top **Live Controls** window lets you change pen colour and width, undo, or clear while presenting; it is not captured by OBS. Press `F11` or `Escape` in the output window to close it. OBS configuration remains manual.

## Troubleshooting and limitations

- If a camera cannot open, close other programs using it, select another camera index, and try again.
- Good lighting and keeping one hand visible improve tracking. Pinch thresholds use hysteresis to reduce flicker.
- This prototype supports one image at a time and does not provide recording, background removal, or direct OBS control.
- Webcam and gesture operation depend on local camera hardware and should be verified on the presentation machine.
