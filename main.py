"""Air_Board application entry point."""
import tkinter as tk
from tkinter import messagebox

from app import AirBoardApp


def main() -> None:
    root = tk.Tk()
    try:
        AirBoardApp(root)
        root.mainloop()
    except Exception as exc:  # Keep startup failures readable for presenters.
        try:
            messagebox.showerror("Air_Board startup error", str(exc), parent=root)
        finally:
            root.destroy()
        raise


if __name__ == "__main__":
    main()
