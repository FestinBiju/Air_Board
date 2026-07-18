# Air_Board Project Instructions

## Project Goal

Build a simple and reliable Python desktop application called **Air_Board**.

Air_Board allows a presenter to:

- View their live webcam feed
- Draw and write over the webcam video using hand gestures
- Add an image to the video
- Annotate over the added image using air drawing
- Change drawing settings while the application is running
- Display a clean preview that can be captured using OBS Window Capture

The project must be functional enough to build and demonstrate within approximately one hour.

## Core User Experience

The expected workflow is:

1. The user launches Air_Board.
2. The user starts the webcam.
3. The index fingertip acts as a cursor.
4. Pinching the thumb and index finger starts drawing.
5. Separating the fingers stops drawing.
6. The drawing remains visible on the webcam feed.
7. The user can change the pen colour and stroke width in real time.
8. The user can add one image to the video.
9. The user can reposition and resize the image using UI controls.
10. The user can draw over the image.
11. The user can clear or undo drawings.
12. The user can enter a clean presentation mode for OBS capture.

## Technology Requirements

Use:

- Python 3.11
- Tkinter
- OpenCV
- MediaPipe
- NumPy
- Pillow

Keep `requirements.txt` minimal:

```text
opencv-python
mediapipe
numpy
Pillow