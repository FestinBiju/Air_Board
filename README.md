# Air_Board

Air_Board is a lightweight Windows desktop prototype for drawing in the air over a live webcam feed. It is designed for capture with OBS Window Capture; it does not create a virtual camera itself.

## Features

- Mirrored in-app webcam preview with one-hand MediaPipe tracking
- Green index-finger cursor; red cursor while pinching to draw
- Persistent, anti-aliased strokes with clear and undo
- Live pen-colour and 1–25 px stroke-width controls
- One PNG/JPG/JPEG overlay with live X/Y position and scale controls
- PNG alpha support; annotations render above the overlay
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

## Controls

- `C`: clear drawings
- `Ctrl+Z`: undo last completed stroke
- `I`: add or replace image
- `R`: remove image
- `L`: toggle landmarks
- `F11`: presentation mode
- `Escape`: leave presentation mode, or close the app normally

Use **Choose Pen Colour** and **Stroke width** before beginning a new stroke. Existing strokes retain their own settings. Add an image and adjust its X, Y, and scale sliders; drawing is always composited over it.

## OBS setup

Open OBS Studio, add a Window Capture source, select the Air_Board window, click Start Virtual Camera, and choose OBS Virtual Camera in your meeting app.

For a clean capture, press `F11` after setting up the feed. OBS configuration remains manual.

## Troubleshooting and limitations

- If a camera cannot open, close other programs using it, select another camera index, and try again.
- Good lighting and keeping one hand visible improve tracking. Pinch thresholds use hysteresis to reduce flicker.
- This prototype supports one image at a time and does not provide recording, background removal, or direct OBS control.
- Webcam and gesture operation depend on local camera hardware and should be verified on the presentation machine.
