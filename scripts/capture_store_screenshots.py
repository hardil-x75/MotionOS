from __future__ import annotations

import time
from pathlib import Path
from tkinter import Toplevel, ttk

from PIL import ImageGrab

from hands_free_control.app import HandsFreeApp
from hands_free_control import config


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = REPO_ROOT / "store-assets"
SCREENSHOT_DIR = ASSET_DIR / "screenshots"
LOGO_DIR = ASSET_DIR / "logos"


def find_notebook(widget):
    if isinstance(widget, ttk.Notebook):
        return widget
    for child in widget.winfo_children():
        found = find_notebook(child)
        if found:
            return found
    return None


def capture_widget(widget, path: Path) -> None:
    widget.update_idletasks()
    widget.lift()
    widget.focus_force()
    time.sleep(0.35)
    x = widget.winfo_rootx()
    y = widget.winfo_rooty()
    width = widget.winfo_width()
    height = widget.winfo_height()
    image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
    image.save(path)


def prepare_demo_state(app: HandsFreeApp) -> None:
    app.status_text.set("Ready")
    app.hand_label.configure(text="Hand: ready")
    app.gesture_label.configure(text="Gesture: none")
    app.voice_label.configure(text="Voice: optional")
    app.performance_label.configure(text="FPS: 0.0")
    app.preview.configure(text="Camera preview appears after Start.\nMove your hand to control your cursor.")
    if hasattr(app, "activity_listbox"):
        app.activity_listbox.delete(0, "end")
        app.activity_listbox.insert("end", "Ready for beta testing")
        app.activity_listbox.insert("end", "Camera and gestures start together")
        app.activity_listbox.insert("end", "Voice commands are optional")


def main() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    LOGO_DIR.mkdir(parents=True, exist_ok=True)

    icon_png = REPO_ROOT / "src" / "hands_free_control" / "assets" / "app-icon.png"
    if icon_png.exists():
        (LOGO_DIR / "x75-motionos-logo.png").write_bytes(icon_png.read_bytes())

    # Keep screenshots consistent and avoid carrying active beta runtime state.
    config.voice_enabled = False
    config.gestures_enabled = True

    app = HandsFreeApp()
    app.geometry("1366x768+80+60")
    app.update()
    prepare_demo_state(app)

    notebook = find_notebook(app)
    if notebook is None:
        raise RuntimeError("Could not find app notebook for tab screenshots.")

    notebook.select(0)
    app.update()
    capture_widget(app, SCREENSHOT_DIR / "01-main-screen.png")

    notebook.select(1)
    app.update()
    capture_widget(app, SCREENSHOT_DIR / "02-advanced-settings.png")

    notebook.select(2)
    app.update()
    capture_widget(app, SCREENSHOT_DIR / "03-custom-gestures.png")

    app._show_how_to_use()
    app.update()
    manual = next((child for child in app.winfo_children() if isinstance(child, Toplevel)), None)
    if manual is None:
        raise RuntimeError("Could not open manual dialog.")
    manual.geometry("900x720+140+80")
    manual.update()
    capture_widget(manual, SCREENSHOT_DIR / "04-how-to-use-manual.png")
    manual.destroy()

    app.destroy()

    print(f"screenshots={SCREENSHOT_DIR}")
    print(f"logos={LOGO_DIR}")


if __name__ == "__main__":
    main()
