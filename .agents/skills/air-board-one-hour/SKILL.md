---

name: air-board-one-hour
description: Build, debug, test, and simplify the AirCanvas Python webcam application. Use when working on webcam capture, MediaPipe hand tracking, pinch-to-draw gestures, OpenCV frame composition, Tkinter live controls, image overlays, annotation, presentation mode, or OBS Window Capture compatibility. Prioritize a working one-hour prototype and avoid unnecessary architecture.
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# AirCanvas One-Hour Prototype

Build and maintain a reliable Python desktop prototype that lets users draw over their live webcam video using hand gestures and place an image on the video for annotation.

The final preview will be captured with OBS Window Capture. Do not create or integrate a custom virtual camera.

## Primary objective

Deliver a working application as quickly as possible.

The essential workflow is:

1. Open the physical webcam.
2. Display a mirrored live preview inside Tkinter.
3. Track one hand using MediaPipe Hands.
4. Use the index fingertip as the cursor.
5. Draw when the thumb and index finger are pinched.
6. Stop drawing when the pinch is released.
7. Preserve completed drawings between frames.
8. Load one image onto the webcam feed.
9. Move and resize the image using live UI controls.
10. Allow drawings to appear over the image.
11. Show a clean presentation view that OBS can capture.

## Time constraint

Treat this as a one-hour prototype.

Prioritize in this order:

1. Application launches.
2. Webcam works.
3. Hand tracking works.
4. Pinch drawing works.
5. Clear and undo work.
6. Runtime colour and width controls work.
7. Image loading works.
8. Runtime image positioning and resizing work.
9. Presentation mode works.
10. Visual polish and optional improvements.

Do not spend time polishing optional functionality until all essential features work.

## Required technologies

Use:

* Python 3.11
* Tkinter
* OpenCV
* MediaPipe
* NumPy
* Pillow

Keep `requirements.txt` minimal:

```text
opencv-python
mediapipe
numpy
Pillow
```

Do not introduce additional packages unless an existing requirement cannot reasonably solve the problem.

## Architecture

Use this simple structure:

```text
AirCanvas/
├── main.py
├── app.py
├── hand_tracker.py
├── canvas_manager.py
├── image_manager.py
├── requirements.txt
└── README.md
```

Responsibilities:

### `main.py`

* Application entry point
* Create the Tkinter root
* Start the main application
* Catch fatal startup errors

### `app.py`

* Main window
* Camera controls
* Live preview
* Tkinter `after()` frame loop
* Runtime settings
* Frame composition
* Presentation mode
* Cleanup

### `hand_tracker.py`

* MediaPipe Hands initialization
* Landmark detection
* Index fingertip position
* Thumb-tip position
* Pinch detection
* Coordinate smoothing

### `canvas_manager.py`

* Active stroke
* Completed stroke history
* Rendering
* Clear
* Undo

### `image_manager.py`

* Image loading
* Aspect-ratio-preserving resizing
* Positioning
* Alpha blending
* Image removal

Do not add design patterns, services, repositories, controllers, dependency-injection systems, plugins, databases, or unnecessary abstraction layers.

## Camera rules

* Default to camera index `0`.
* Prefer 1280 × 720.
* Allow fallback to the resolution actually supplied by the camera.
* Mirror the webcam frame horizontally.
* Use Tkinter `after()` rather than blocking the main thread.
* Do not use `cv2.imshow()` as the main application window.
* Always release `cv2.VideoCapture` when stopping or closing.
* Do not reopen the camera every frame.
* Handle failed frame reads without crashing the UI.

## MediaPipe configuration

Use one hand only:

```python
max_num_hands=1
model_complexity=0
min_detection_confidence=0.6
min_tracking_confidence=0.6
```

Use:

* `INDEX_FINGER_TIP`
* `THUMB_TIP`

The index fingertip controls the cursor.

Calculate pinch distance in frame pixels.

Use separate thresholds to reduce rapid state switching:

```python
PINCH_START_THRESHOLD = 40
PINCH_RELEASE_THRESHOLD = 55
```

Drawing starts below the start threshold and remains active until the distance exceeds the release threshold.

This hysteresis should prevent flickering between drawing and tracking states.

## Cursor smoothing

Use lightweight exponential smoothing:

```python
smoothed_x = alpha * current_x + (1 - alpha) * previous_x
smoothed_y = alpha * current_y + (1 - alpha) * previous_y
```

Use an initial `alpha` around `0.4`.

Do not make smoothing so strong that the cursor feels delayed.

Reset smoothing when the hand disappears for several consecutive frames.

## Drawing behaviour

Display:

* Green cursor while tracking
* Red cursor while drawing
* “No hand detected” when no hand is visible

When the pinch starts:

1. Create an active stroke.
2. Store the currently selected colour.
3. Store the currently selected width.
4. Add the smoothed cursor position.

While the pinch remains active:

1. Add cursor points to the active stroke.
2. Connect consecutive points using `cv2.line`.
3. Use `cv2.LINE_AA`.

When the pinch ends:

1. Complete the active stroke.
2. Add it to stroke history.
3. Clear the previous drawing point.
4. Ensure the next stroke is not connected to the previous stroke.

Do not mutate the colour or width of an active or completed stroke when the user changes settings.

New settings apply only to future strokes.

## Stroke model

Use a simple structure:

```python
@dataclass
class Stroke:
    points: list[tuple[int, int]]
    color: tuple[int, int, int]
    width: int
```

Store colour internally in OpenCV BGR format.

Implement:

* `start_stroke`
* `add_point`
* `finish_stroke`
* `undo`
* `clear`
* `render`

Undo removes the most recent completed stroke.

Re-render the canvas from stored strokes after undo or clear.

Avoid storing a full video frame for every drawing action.

## Frame composition order

Compose every output frame in this order:

1. Mirrored webcam frame
2. Loaded image overlay
3. Stored drawing strokes
4. Active drawing stroke
5. Optional MediaPipe landmarks
6. Cursor
7. Minimal status text

This order ensures that annotations appear over the imported image.

Do not accidentally process MediaPipe using a frame that has already been covered with drawings or UI elements. Hand detection should use the clean webcam image whenever possible.

## Runtime settings

Provide controls for:

* Pen colour
* Stroke width
* Add image
* Remove image
* Image X position
* Image Y position
* Image scale
* Clear canvas
* Undo
* Landmark visibility
* Start camera
* Stop camera
* Presentation mode

All settings must update while the camera is running.

Do not require an application restart.

### Pen colour

Use `tkinter.colorchooser`.

Convert the selected RGB value to BGR for OpenCV.

Canceling the colour dialog must leave the existing colour unchanged.

### Stroke width

Use a slider from 1 to 25 pixels.

Changing it affects the next stroke immediately.

### Image controls

Only one active image is required.

Support:

* PNG
* JPG
* JPEG

Preserve PNG transparency.

Provide:

* Horizontal-position slider
* Vertical-position slider
* Scale slider from approximately 20% to 150%

The image must update immediately when sliders move.

Do not reload the source image from disk every frame.

Store the original image and only regenerate the resized copy when scale changes.

Clamp the final image placement so invalid array slicing cannot crash the application.

## Image overlay rules

Support both:

* Three-channel BGR images
* Four-channel BGRA images

For BGRA images, alpha-blend with the webcam frame.

Handle partial placement outside the frame by clipping the source and destination regions.

Do not assume the entire image is inside the video dimensions.

If loading fails, show a Tkinter message box and keep the previous application state.

## Tkinter performance rules

* Create widgets once.
* Do not rebuild widgets every frame.
* Keep a reference to the current `ImageTk.PhotoImage`.
* Use `after()` to schedule the next frame.
* Cancel scheduled callbacks when the window closes.
* Do not run multiple frame loops simultaneously.
* Disable Start Camera while the camera is already running.
* Update only values that have changed.
* Keep frame processing separate from widget construction.

## Presentation mode

Presentation mode should:

* Hide the settings panel.
* Enlarge the video preview.
* Keep the output window suitable for OBS Window Capture.
* Avoid showing unnecessary controls over the video.
* Allow Escape to exit presentation mode.

Do not open a second webcam instance for presentation mode.

Continue using the existing capture and processing loop.

## Keyboard shortcuts

Implement:

```text
C       Clear drawings
Ctrl+Z  Undo last stroke
I       Add or replace image
R       Remove image
L       Toggle hand landmarks
F11     Toggle presentation mode
Escape  Exit presentation mode, or close if already in normal mode
```

Avoid triggering shortcuts while the user is actively interacting with an entry widget or modal dialog.

## Reliability rules

Before adding features, verify that existing functionality still works.

After every meaningful change:

1. Run a Python syntax check.
2. Run the application.
3. Confirm imports succeed.
4. Confirm the Tkinter window opens.
5. Confirm camera startup does not block the UI.
6. Confirm closing the window releases the camera.

Use:

```bash
python -m compileall .
python main.py
```

Do not claim that webcam or gesture behaviour was tested if no camera is available in the execution environment.

When hardware testing is unavailable:

* Test imports.
* Test class construction where possible.
* Test canvas functions using generated NumPy images.
* Test image overlay functions using generated BGRA and BGR images.
* Clearly state which hardware-dependent behaviour requires manual verification.

## Debugging sequence

When the application fails, debug in this order:

1. Syntax and import errors
2. Python version
3. Missing packages
4. Camera opening
5. Frame dimensions
6. Pillow/Tkinter image conversion
7. MediaPipe initialization
8. Landmark coordinates
9. Pinch-state transitions
10. Canvas rendering
11. Image clipping and alpha blending
12. Application shutdown

Fix the smallest underlying issue rather than rewriting the project.

## Common problems to prevent

### Tkinter preview is blank

Retain a persistent reference:

```python
self.preview_photo = ImageTk.PhotoImage(image)
self.preview_label.configure(image=self.preview_photo)
```

### UI freezes

Do not use an infinite `while` loop in the Tkinter main thread.

### Lines connect unexpectedly

Reset the previous point whenever:

* Pinch is released
* Hand tracking is lost
* Camera stops
* Canvas is cleared

### Colour appears incorrect

Convert RGB from Tkinter to BGR before drawing with OpenCV.

### Image overlay crashes

Clip all overlay coordinates before NumPy slicing.

### Camera remains active after exit

Call:

```python
capture.release()
```

Also close MediaPipe resources and cancel pending Tkinter callbacks.

### Hand tracking becomes slow

Reduce the processing resolution while retaining a larger display resolution if necessary.

Do not add multiprocessing unless the simple implementation is demonstrably unusable.

## Completion criteria

Do not consider the project complete until:

* `python main.py` starts successfully.
* The UI remains responsive.
* The camera can be started and stopped.
* The webcam preview is mirrored.
* The cursor follows the index fingertip.
* Pinching creates a stroke.
* Releasing ends the stroke.
* Separate strokes are not connected.
* Drawings persist.
* Clear works.
* Undo works.
* Runtime colour changes work.
* Runtime width changes work.
* An image can be loaded.
* The image can be repositioned.
* The image can be resized.
* The image can be removed.
* Drawings render over the image.
* Landmark visibility can be changed at runtime.
* Presentation mode provides a clean preview.
* Closing the app releases resources.
* README instructions match the actual application.

## Scope exclusions

Do not build:

* Custom virtual camera drivers
* Direct OBS integration
* Google Meet APIs
* Microsoft Teams APIs
* User authentication
* Cloud storage
* Databases
* Voice commands
* OCR
* Handwriting recognition
* Gesture-controlled image resizing
* Multiple simultaneous images
* Background segmentation
* Recording
* Streaming
* Installers
* Auto-update systems
* Model training
* 3D rendering

## Final response

After completing the work, report:

1. Files created or modified
2. Commands used
3. Tests performed
4. Features confirmed working
5. Hardware-dependent items requiring manual verification
6. Remaining limitations

Do not respond with code snippets alone. Create or modify the actual project files and run all feasible checks.
