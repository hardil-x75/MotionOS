# ============================================================
# config.py - Central configuration and shared state
# ============================================================

import threading
from dataclasses import dataclass
import json
import os


DEFAULT_CUSTOM_GESTURE_MAPPING = {
    "pinch": "Left click",
    "double_pinch": "Left click",
    "pinch_hold": "Drag / select",
    "select_hold": "Drag / select",
    "scroll_up": "Scroll up",
    "scroll_down": "Scroll down",
    "swipe_right": "Switch desktop",
    "swipe_left": "Switch desktop",
    "task_view": "Task view",
    "zoom_in": "Zoom in",
    "zoom_out": "Zoom out",
    "right_click": "Right click",
}
DEFAULT_PROFILE_NAME = "Default"


def _user_data_dir():
    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(root, "X75MotionOS")
    return os.path.join(os.path.expanduser("~"), ".x75_motionos")


def _prepare_data_dir():
    def writable(path):
        os.makedirs(path, exist_ok=True)
        marker = os.path.join(path, ".write_test")
        with open(marker, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(marker)
        return path

    try:
        return writable(_user_data_dir())
    except OSError:
        return writable(os.path.join(os.getcwd(), ".appdata"))


DATA_DIR = _prepare_data_dir()
CONFIG_FILE = os.path.join(DATA_DIR, "settings.json")


@dataclass
class AppConfig:
    """Central configuration object - all modules read from this."""

    # --- Camera ---
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    target_fps: int = 30

    # --- Cursor ---
    cursor_smoothing: float = 0.25        # 0.0 = instant, 1.0 = very smooth
    cursor_sensitivity: float = 1.5       # multiplier
    dead_zone_radius: int = 8             # pixels of dead zone
    acceleration_enabled: bool = True
    acceleration_factor: float = 1.3

    # --- Gestures ---
    gestures_enabled: bool = True
    gesture_sensitivity: float = 0.7     # 0-1, threshold for detection
    click_threshold: float = 0.045       # thumb+index distance to enter pinch
    click_release_threshold: float = 0.065  # distance to finish a pinch cleanly
    click_min_hold_ms: int = 35          # ignore one-frame pinch noise
    click_cooldown_ms: int = 140         # delay between click releases
    selection_hold_ms: int = 180         # hold the second quick pinch to select
    gesture_cooldown_ms: int = 600        # ms between same gesture
    confidence_min: float = 0.75
    scroll_speed: int = 6
    scroll_join_threshold: float = 0.065    # index+middle distance to enter scroll mode
    scroll_release_threshold: float = 0.09  # index+middle distance to leave scroll mode
    scroll_motion_threshold: float = 0.004  # lower = reacts to smaller 2-finger movement
    scroll_cooldown_ms: int = 12            # lower = more frequent scroll events
    scroll_motion_multiplier: float = 220.0 # higher = faster scroll for same hand movement
    scroll_speed_multiplier: float = 12.0   # higher = fast hand movement scrolls more pages
    scroll_max_units: int = 28              # cap per scroll event to avoid huge jumps
    drag_hold_ms: int = 600              # ms to hold pinch before drag

    # --- Voice ---
    voice_enabled: bool = False
    voice_engine: str = "google"         # "google", "whisper", "vosk"
    wake_word_mode: bool = False
    wake_word: str = "computer"
    microphone_index: int = 0
    voice_timeout: float = 5.0
    voice_phrase_limit: float = 10.0
    voice_confirmation_sound: bool = True
    dangerous_voice_commands_enabled: bool = False

    # --- Screen ---
    screen_width: int = 1920
    screen_height: int = 1080
    # Calibration offsets (set by calibration routine)
    map_x_min: float = 0.1
    map_x_max: float = 0.9
    map_y_min: float = 0.1
    map_y_max: float = 0.9

    # --- Debug / Logging ---
    debug_mode: bool = False
    show_overlay: bool = True
    log_level: str = "INFO"
    custom_gesture_mapping: dict | None = None
    active_profile: str = DEFAULT_PROFILE_NAME
    profiles: dict | None = None

    # ------------------------------------------------------------------ #
    def save(self):
        """Persist settings to disk."""
        if self.custom_gesture_mapping is None:
            self.custom_gesture_mapping = DEFAULT_CUSTOM_GESTURE_MAPPING.copy()
        if self.profiles is None:
            self.profiles = {}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, indent=2)

    def load(self):
        """Load settings from disk (if available)."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(self, k):
                        setattr(self, k, v)
            except Exception:
                pass  # Fall back to defaults
        if not isinstance(self.custom_gesture_mapping, dict):
            self.custom_gesture_mapping = DEFAULT_CUSTOM_GESTURE_MAPPING.copy()
        else:
            merged = DEFAULT_CUSTOM_GESTURE_MAPPING.copy()
            merged.update(self.custom_gesture_mapping)
            self.custom_gesture_mapping = merged
        if not isinstance(self.active_profile, str) or not self.active_profile.strip():
            self.active_profile = DEFAULT_PROFILE_NAME
        if not isinstance(self.profiles, dict):
            self.profiles = {}

# Singleton config
config = AppConfig()
config.load()


# ------------------------------------------------------------------ #
# Shared runtime state - all threads read/write this via lock
# ------------------------------------------------------------------ #
class RuntimeState:
    """Thread-safe shared runtime state."""

    def __init__(self):
        self._lock = threading.Lock()

        # Camera feed (latest frame as numpy array)
        self.frame = None
        self.overlay_frame = None

        # Hand tracking
        self.hand_detected = False
        self.finger_pos = (0.0, 0.0)        # normalized (0-1)
        self.cursor_pos = (960, 540)         # screen pixels
        self.active_gesture = None
        self.gesture_confidence = 0.0

        # System metrics
        self.fps = 0.0
        self.latency_ms = 0.0
        self.cpu_usage = 0.0

        # Voice
        self.last_command = ""
        self.voice_active = False
        self.listening = False

        # Control flags
        self.running = True
        self.camera_running = False
        self.voice_running = False

        # Command history (max 50)
        self.command_history: list[str] = []

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    def get(self, key):
        with self._lock:
            return getattr(self, key, None)

    def add_command(self, cmd: str):
        with self._lock:
            self.command_history.append(cmd)
            if len(self.command_history) > 50:
                self.command_history.pop(0)
            self.last_command = cmd

    def reset_runtime(self):
        """Reset transient state before a fresh app run."""
        with self._lock:
            self.frame = None
            self.overlay_frame = None
            self.hand_detected = False
            self.finger_pos = (0.0, 0.0)
            self.cursor_pos = (config.screen_width // 2, config.screen_height // 2)
            self.active_gesture = None
            self.gesture_confidence = 0.0
            self.fps = 0.0
            self.latency_ms = 0.0
            self.cpu_usage = 0.0
            self.last_command = ""
            self.voice_active = False
            self.listening = False
            self.running = True
            self.camera_running = False
            self.voice_running = False


state = RuntimeState()
