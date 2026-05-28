# ============================================================
# mouse_controller.py - Low-level mouse control via pynput or pyautogui
# ============================================================

import threading

try:
    from pynput.mouse import Button, Controller as MouseController
    _PYNPUT_AVAILABLE = True
except ImportError:
    import pyautogui

    class Button:
        left = "left"
        right = "right"

    MouseController = None
    _PYNPUT_AVAILABLE = False

try:
    from .logger import log
except ImportError:
    from logger import log


class MouseCtrl:
    """Thread-safe wrapper around pynput mouse controller."""

    def __init__(self):
        self._mouse = MouseController() if _PYNPUT_AVAILABLE else None
        self._lock = threading.Lock()
        self._dragging = False

    def move(self, x: int, y: int):
        with self._lock:
            try:
                if _PYNPUT_AVAILABLE:
                    self._mouse.position = (x, y)
                else:
                    pyautogui.moveTo(x, y)
            except Exception as e:
                log.error(f"Mouse move error: {e}")

    def click(self, button=Button.left, count: int = 1):
        with self._lock:
            try:
                if _PYNPUT_AVAILABLE:
                    self._mouse.click(button, count)
                else:
                    pyautogui.click(button=button, clicks=count)
                log.debug(f"Mouse click: {button} x{count}")
            except Exception as e:
                log.error(f"Mouse click error: {e}")

    def right_click(self):
        self.click(Button.right)

    def double_click(self):
        self.click(Button.left, 2)

    def press(self):
        """Start drag."""
        with self._lock:
            try:
                if _PYNPUT_AVAILABLE:
                    self._mouse.press(Button.left)
                else:
                    pyautogui.mouseDown(button=Button.left)
                self._dragging = True
                log.debug("Mouse pressed (drag start)")
            except Exception as e:
                log.error(f"Mouse press error: {e}")

    def release(self):
        """End drag."""
        with self._lock:
            try:
                if _PYNPUT_AVAILABLE:
                    self._mouse.release(Button.left)
                else:
                    pyautogui.mouseUp(button=Button.left)
                self._dragging = False
                log.debug("Mouse released (drag end)")
            except Exception as e:
                log.error(f"Mouse release error: {e}")

    def scroll(self, dx: int = 0, dy: int = 0):
        with self._lock:
            try:
                if _PYNPUT_AVAILABLE:
                    self._mouse.scroll(-dx, -dy)
                else:
                    pyautogui.hscroll(-dx)
                    pyautogui.scroll(-dy)
            except Exception as e:
                log.error(f"Mouse scroll error: {e}")


mouse_ctrl = MouseCtrl()
