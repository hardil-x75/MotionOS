# ============================================================
# action_executor.py - Maps gestures/voice to OS actions
# ============================================================

import subprocess
import webbrowser
import platform

import pyautogui

try:
    from .config import config, state
    from .logger import log
    from .mouse_controller import mouse_ctrl
except ImportError:
    from config import config, state
    from logger import log
    from mouse_controller import mouse_ctrl


class Gesture:
    PINCH = "pinch"
    DOUBLE_PINCH = "double_pinch"
    PINCH_HOLD = "pinch_hold"
    SELECT_HOLD = "select_hold"
    TWO_SCROLL_UP = "scroll_up"
    TWO_SCROLL_DN = "scroll_down"
    THREE_SWIPE_R = "swipe_right"
    THREE_SWIPE_L = "swipe_left"
    FOUR_TASK = "task_view"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    RIGHT_CLICK = "right_click"

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0

OS = platform.system()  # "Windows", "Darwin", "Linux"


# ------------------------------------------------------------------ #
# Sound feedback
# ------------------------------------------------------------------ #
def _play_beep():
    """Short confirmation beep (cross-platform best-effort)."""
    if not config.voice_confirmation_sound:
        return
    try:
        if OS == "Windows":
            import winsound
            winsound.Beep(1000, 80)
        elif OS == "Darwin":
            subprocess.Popen(["afplay", "/System/Library/Sounds/Tink.aiff"])
        else:
            subprocess.Popen(["aplay", "-q", "/usr/share/sounds/alsa/Front_Left.wav"])
    except Exception:
        pass


# ------------------------------------------------------------------ #
# Gesture to action map
# ------------------------------------------------------------------ #
class ActionExecutor:

    def execute_gesture(self, gesture: str, amount: int | None = None):
        """Dispatch a gesture to the appropriate OS action."""
        action_name = self._mapped_action(gesture)
        fn = self._action_callable(gesture, action_name, amount)
        if fn:
            try:
                fn()
                state.add_command(f"[GESTURE] {gesture} -> {action_name}")
            except Exception as e:
                log.error(f"Action error for {gesture} -> {action_name}: {e}")

    def _mapped_action(self, gesture: str) -> str:
        mapping = getattr(config, "custom_gesture_mapping", None) or {}
        fallback = {
            Gesture.PINCH: "Left click",
            Gesture.DOUBLE_PINCH: "Left click",
            Gesture.PINCH_HOLD: "Drag / select",
            Gesture.SELECT_HOLD: "Drag / select",
            Gesture.RIGHT_CLICK: "Right click",
            Gesture.TWO_SCROLL_UP: "Scroll up",
            Gesture.TWO_SCROLL_DN: "Scroll down",
            Gesture.THREE_SWIPE_R: "Switch desktop",
            Gesture.THREE_SWIPE_L: "Switch desktop",
            Gesture.FOUR_TASK: "Task view",
            Gesture.ZOOM_IN: "Zoom in",
            Gesture.ZOOM_OUT: "Zoom out",
        }
        return mapping.get(gesture) or fallback.get(gesture, "No action")

    def _action_callable(self, gesture: str, action_name: str, amount: int | None = None):
        switch_desktop = self._prev_desktop if gesture == Gesture.THREE_SWIPE_L else self._next_desktop
        actions = {
            "Left click": self._left_click,
            "Double click": self._double_click,
            "Right click": self._right_click,
            "Scroll up": lambda: self._scroll_up(amount),
            "Scroll down": lambda: self._scroll_down(amount),
            "Switch desktop": switch_desktop,
            "Previous desktop": self._prev_desktop,
            "Task view": self._task_view,
            "Zoom in": self._zoom_in,
            "Zoom out": self._zoom_out,
            "Drag / select": None,
            "No action": None,
        }
        return actions.get(action_name)

    # ---- Mouse ----
    def _left_click(self):
        mouse_ctrl.click()

    def _double_click(self):
        mouse_ctrl.double_click()

    def _right_click(self):
        mouse_ctrl.right_click()

    # ---- Scroll ----
    def _scroll_up(self, amount: int | None = None):
        mouse_ctrl.scroll(0, amount or config.scroll_speed)

    def _scroll_down(self, amount: int | None = None):
        mouse_ctrl.scroll(0, -(amount or config.scroll_speed))

    # ---- Desktop navigation ----
    def _next_desktop(self):
        if OS == "Windows":
            pyautogui.hotkey("ctrl", "win", "right")
        elif OS == "Darwin":
            pyautogui.hotkey("ctrl", "right")
        else:
            pyautogui.hotkey("super", "ctrl", "right")
        log.debug("Next desktop")

    def _prev_desktop(self):
        if OS == "Windows":
            pyautogui.hotkey("ctrl", "win", "left")
        elif OS == "Darwin":
            pyautogui.hotkey("ctrl", "left")
        else:
            pyautogui.hotkey("super", "ctrl", "left")
        log.debug("Prev desktop")

    def _task_view(self):
        if OS == "Windows":
            pyautogui.hotkey("win", "tab")
        elif OS == "Darwin":
            pyautogui.hotkey("ctrl", "up")
        else:
            pyautogui.hotkey("super", "w")
        log.debug("Task view")

    # ---- Zoom ----
    def _zoom_in(self):
        pyautogui.hotkey("ctrl", "+")

    def _zoom_out(self):
        pyautogui.hotkey("ctrl", "-")

    # ================================================================ #
    # Voice command executor
    # ================================================================ #
    def _clean_voice_command(self, command: str) -> str:
        cmd = command.lower().strip()
        # Clean common polite filler phrases and noise
        fillers = ["please", "can you", "could you", "would you", "now", "the", "a", "an", "hey", "computer", "system"]
        words = cmd.split()
        cleaned_words = [w for w in words if w not in fillers]
        return " ".join(cleaned_words)

    def execute_voice(self, command: str):
        """Parse and execute a voice command string."""
        raw_cmd = command.lower().strip()
        
        # 1. Check typing/dictate first with raw string to preserve exact text
        if raw_cmd.startswith("type "):
            text = command[5:]
            pyautogui.typewrite(text, interval=0.03)
            state.add_command(f"[VOICE] type: {text}")
            _play_beep()
            return
        if raw_cmd.startswith("dictate "):
            text = command[8:]
            pyautogui.typewrite(text, interval=0.03)
            state.add_command(f"[VOICE] dictate: {text}")
            _play_beep()
            return

        # 2. Clean input command for matching other system actions
        cmd = self._clean_voice_command(raw_cmd)
        log.info(f"Voice command processed: '{cmd}' (raw: '{raw_cmd}')")
        state.add_command(f"[VOICE] {cmd}")
        _play_beep()

        # --- Open apps ---
        if cmd.startswith("open ") or cmd.startswith("launch ") or cmd.startswith("start ") or cmd.startswith("run "):
            app = cmd
            for verb in ("open ", "launch ", "start ", "run "):
                if app.startswith(verb):
                    app = app[len(verb):].strip()
                    break
            self._open_app(app)
            return

        # --- Browser search ---
        if cmd.startswith("search ") or cmd.startswith("google ") or cmd.startswith("find ") or cmd.startswith("look up "):
            query = cmd
            for prefix in ("search for ", "search ", "google search ", "google ", "find ", "look up "):
                if query.startswith(prefix):
                    query = query[len(prefix):]
            query = query.strip()
            
            # YouTube check within search
            if "youtube" in cmd:
                query = query.replace("on youtube", "").replace("youtube", "").strip()
                webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
                return
                
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return

        if "youtube" in cmd and "for" in cmd:
            query = cmd.split("for", 1)[-1].strip()
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            return

        # --- Website navigation ---
        if cmd.startswith("go to ") or cmd.startswith("open website ") or cmd.startswith("visit "):
            site = cmd
            for prefix in ("go to ", "open website ", "visit "):
                if site.startswith(prefix):
                    site = site[len(prefix):]
            site = site.strip()
            if not site.startswith("http"):
                site = "https://" + site
            webbrowser.open(site)
            return

        # --- Clipboard & Selection ---
        if cmd in ("copy", "copy that", "copy text", "copy selection"):
            pyautogui.hotkey("ctrl", "c")
        elif cmd in ("paste", "paste that", "paste text"):
            pyautogui.hotkey("ctrl", "v")
        elif cmd in ("cut", "cut that"):
            pyautogui.hotkey("ctrl", "x")
        elif cmd in ("undo", "undo that", "revert"):
            pyautogui.hotkey("ctrl", "z")
        elif cmd in ("redo", "redo that"):
            pyautogui.hotkey("ctrl", "y")
        elif cmd in ("select all", "select everything"):
            pyautogui.hotkey("ctrl", "a")

        # --- Deletion ---
        elif cmd in ("delete", "delete that", "backspace", "erase"):
            pyautogui.press("backspace")
        elif cmd in ("delete word", "erase word"):
            pyautogui.hotkey("ctrl", "backspace")
        elif cmd in ("delete line", "erase line"):
            pyautogui.hotkey("shift", "home")
            pyautogui.press("backspace")

        # --- Keys ---
        elif cmd in ("enter", "press enter", "submit", "confirm"):
            pyautogui.press("enter")
        elif cmd in ("escape", "press escape", "cancel", "quit"):
            pyautogui.press("escape")
        elif cmd in ("tab", "press tab", "next field"):
            pyautogui.press("tab")
        elif cmd in ("space", "press space", "spacebar"):
            pyautogui.press("space")

        # --- Navigation ---
        elif cmd in ("scroll up", "scroll up please", "page up"):
            self._scroll_up()
        elif cmd in ("scroll down", "scroll down please", "page down"):
            self._scroll_down()
        elif cmd in ("page up key",):
            pyautogui.press("pageup")
        elif cmd in ("page down key",):
            pyautogui.press("pagedown")
        elif cmd in ("go back", "previous page"):
            pyautogui.hotkey("alt", "left")
        elif cmd in ("go forward", "next page"):
            pyautogui.hotkey("alt", "right")

        # --- Tabs ---
        elif cmd in ("next tab", "switch tab", "forward tab"):
            pyautogui.hotkey("ctrl", "tab")
        elif cmd in ("previous tab", "prev tab", "backward tab"):
            pyautogui.hotkey("ctrl", "shift", "tab")
        elif cmd in ("new tab", "create tab"):
            pyautogui.hotkey("ctrl", "t")
        elif cmd in ("close tab", "exit tab"):
            pyautogui.hotkey("ctrl", "w")
        elif cmd in ("reopen tab", "restore tab"):
            pyautogui.hotkey("ctrl", "shift", "t")

        # --- Window management ---
        elif cmd in ("minimize", "minimise", "minimize window", "hide window"):
            pyautogui.hotkey("win", "down") if OS == "Windows" else pyautogui.hotkey("super", "h")
        elif cmd in ("maximize", "maximise", "maximize window", "full screen", "restore window"):
            pyautogui.hotkey("win", "up") if OS == "Windows" else pyautogui.hotkey("super", "up")
        elif cmd in ("close window", "close app", "exit app", "quit window"):
            pyautogui.hotkey("alt", "f4") if OS == "Windows" else pyautogui.hotkey("cmd", "q")
        elif cmd in ("new window", "open window"):
            pyautogui.hotkey("ctrl", "n")

        # --- Volume ---
        elif any(k in cmd for k in ("volume up", "louder", "increase volume", "turn up volume", "raise volume")):
            self._volume_up()
        elif any(k in cmd for k in ("volume down", "quieter", "decrease volume", "turn down volume", "lower volume")):
            self._volume_down()
        elif any(k in cmd for k in ("mute volume", "mute", "unmute", "toggle mute")):
            self._volume_mute()

        # --- Brightness ---
        elif any(k in cmd for k in ("brightness up", "brighter", "increase brightness", "turn up brightness")):
            self._brightness_up()
        elif any(k in cmd for k in ("brightness down", "dimmer", "decrease brightness", "turn down brightness")):
            self._brightness_down()

        # --- System Commands ---
        elif cmd in ("shutdown", "shut down", "power off", "turn off computer"):
            self._run_dangerous_voice_action(cmd, self._system_shutdown)
        elif cmd in ("restart", "reboot", "restart computer"):
            self._run_dangerous_voice_action(cmd, self._system_restart)
        elif cmd in ("sleep", "suspend", "suspend computer"):
            self._run_dangerous_voice_action(cmd, self._system_sleep)
        elif cmd in ("lock screen", "lock computer"):
            self._system_lock()

        # --- Desktop navigation (voice) ---
        elif cmd in ("next desktop", "go to next desktop"):
            self._next_desktop()
        elif cmd in ("previous desktop", "go to previous desktop", "prev desktop"):
            self._prev_desktop()
        elif cmd in ("task view", "show tasks", "switch tasks"):
            self._task_view()

        # --- Screenshot ---
        elif cmd in ("screenshot", "take screenshot", "capture screen", "print screen"):
            pyautogui.hotkey("win", "prtsc") if OS == "Windows" else pyautogui.hotkey("ctrl", "shift", "3")

        # --- File manager ---
        elif cmd in ("open file manager", "files", "explorer", "my computer"):
            self._open_app("explorer" if OS == "Windows" else "nautilus" if OS == "Linux" else "finder")

        # --- Punctuation dictation ---
        elif cmd == "period":
            pyautogui.typewrite(".", interval=0.01)
        elif cmd == "comma":
            pyautogui.typewrite(",", interval=0.01)
        elif cmd == "question mark":
            pyautogui.typewrite("?", interval=0.01)
        elif cmd == "exclamation mark":
            pyautogui.typewrite("!", interval=0.01)
        elif cmd == "new line":
            pyautogui.press("enter")

        else:
            log.debug(f"Unknown voice command: '{cmd}'")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _run_dangerous_voice_action(self, command: str, action):
        if not config.dangerous_voice_commands_enabled:
            log.warning(f"Blocked dangerous voice command while safety lock is on: {command}")
            state.add_command(f"[BLOCKED] {command}")
            return
        action()

    def _open_app(self, app: str):
        apps = {
            "chrome":      ["google-chrome", "chrome", "chromium-browser"],
            "firefox":     ["firefox"],
            "notepad":     ["notepad"] if OS == "Windows" else ["gedit", "mousepad"],
            "terminal":    ["gnome-terminal", "konsole", "xterm"] if OS == "Linux" else ["cmd"],
            "calculator":  ["gnome-calculator", "kcalc"] if OS == "Linux" else ["calc"],
            "files":       ["nautilus"] if OS == "Linux" else ["explorer"],
            "settings":    ["gnome-control-center"] if OS == "Linux" else ["ms-settings:"],
            "spotify":     ["spotify"],
            "vscode":      ["code"],
            "word":        ["winword"] if OS == "Windows" else [],
            "excel":       ["excel"] if OS == "Windows" else ["libreoffice --calc"],
        }

        candidates = apps.get(app, [app])
        for candidate in candidates:
            try:
                subprocess.Popen(candidate.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                log.info(f"Opened app: {candidate}")
                return
            except FileNotFoundError:
                continue
        # Final fallback
        try:
            subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log.error(f"Could not open app '{app}': {e}")

    def _volume_up(self):
        if OS == "Windows":
            try:
                from pynput.keyboard import Key, Controller as KB
                kb = KB()
                for _ in range(5):
                    kb.press(Key.media_volume_up)
                    kb.release(Key.media_volume_up)
            except ImportError:
                for _ in range(5):
                    pyautogui.press("volumeup")
        elif OS == "Linux":
            subprocess.run(["amixer", "-q", "sset", "Master", "5%+"])
        elif OS == "Darwin":
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"])

    def _volume_down(self):
        if OS == "Windows":
            try:
                from pynput.keyboard import Key, Controller as KB
                kb = KB()
                for _ in range(5):
                    kb.press(Key.media_volume_down)
                    kb.release(Key.media_volume_down)
            except ImportError:
                for _ in range(5):
                    pyautogui.press("volumedown")
        elif OS == "Linux":
            subprocess.run(["amixer", "-q", "sset", "Master", "5%-"])
        elif OS == "Darwin":
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"])

    def _volume_mute(self):
        if OS == "Windows":
            pyautogui.press("volumemute")
        elif OS == "Linux":
            subprocess.run(["amixer", "-q", "sset", "Master", "toggle"])
        elif OS == "Darwin":
            subprocess.run(["osascript", "-e", "set volume output muted not (output muted of (get volume settings))"])

    def _brightness_up(self):
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness(display=0)[0]
            sbc.set_brightness(min(100, current + 10), display=0)
        except Exception as e:
            log.error(f"Brightness up error: {e}")

    def _brightness_down(self):
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness(display=0)[0]
            sbc.set_brightness(max(0, current - 10), display=0)
        except Exception as e:
            log.error(f"Brightness down error: {e}")

    def _system_shutdown(self):
        if OS == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "10"])
        elif OS == "Darwin":
            subprocess.run(["sudo", "shutdown", "-h", "+1"])
        else:
            subprocess.run(["systemctl", "poweroff"])

    def _system_restart(self):
        if OS == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "10"])
        elif OS == "Darwin":
            subprocess.run(["sudo", "shutdown", "-r", "+1"])
        else:
            subprocess.run(["systemctl", "reboot"])

    def _system_sleep(self):
        if OS == "Windows":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        elif OS == "Darwin":
            subprocess.run(["pmset", "sleepnow"])
        else:
            subprocess.run(["systemctl", "suspend"])

    def _system_lock(self):
        if OS == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif OS == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "q" using {command down, control down}'])
        else:
            subprocess.run(["loginctl", "lock-session"])


executor = ActionExecutor()
