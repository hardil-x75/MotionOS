# ============================================================
# hand_tracker.py - MediaPipe hand tracking & gesture engine
# ============================================================

import time
import math
import threading
import numpy as np
import cv2

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

try:
    from .config import config, state
    from .logger import log
except ImportError:
    from config import config, state
    from logger import log


# ------------------------------------------------------------------ #
# Landmark indices (MediaPipe hand model)
# ------------------------------------------------------------------ #
WRIST         = 0
THUMB_TIP     = 4
INDEX_TIP     = 8
INDEX_MCP     = 5
MIDDLE_TIP    = 12
MIDDLE_MCP    = 9
RING_TIP      = 16
PINKY_TIP     = 20
INDEX_PIP     = 6
MIDDLE_PIP    = 10
RING_PIP      = 14
PINKY_PIP     = 18


# ------------------------------------------------------------------ #
# Gesture names
# ------------------------------------------------------------------ #
class Gesture:
    NONE           = "none"
    PINCH          = "pinch"           # index+thumb close -> click
    DOUBLE_PINCH   = "double_pinch"    # rapid two pinches -> double click
    PINCH_HOLD     = "pinch_hold"      # sustained pinch -> drag
    SELECT_HOLD    = "select_hold"     # second quick pinch held -> select
    TWO_SCROLL_UP  = "scroll_up"       # 2-finger swipe up
    TWO_SCROLL_DN  = "scroll_down"     # 2-finger swipe down
    SCROLL_MODE    = "scroll_mode"     # index+middle held together
    THREE_SWIPE_R  = "swipe_right"     # 3-finger swipe -> next desktop
    THREE_SWIPE_L  = "swipe_left"      # 3-finger swipe -> prev desktop
    FOUR_TASK      = "task_view"        # 4-finger spread -> task view
    ZOOM_IN        = "zoom_in"         # thumb+index spread apart
    ZOOM_OUT       = "zoom_out"        # pinch to close
    FIST           = "fist"            # all fingers closed
    OPEN_PALM      = "open_palm"       # all fingers extended
    RIGHT_CLICK    = "right_click"     # index+middle pinch together
    MINIMIZE       = "minimize"        # swipe down fast
    MAXIMIZE       = "maximize"        # swipe up fast


# ------------------------------------------------------------------ #
# Helper: Euclidean distance between two landmarks
# ------------------------------------------------------------------ #
def _dist(lm, a: int, b: int) -> float:
    ax, ay = lm[a].x, lm[a].y
    bx, by = lm[b].x, lm[b].y
    return math.hypot(ax - bx, ay - by)


def _midpoint(lm, a: int, b: int):
    return ((lm[a].x + lm[b].x) / 2, (lm[a].y + lm[b].y) / 2)


def _finger_up(lm, tip: int, pip: int) -> bool:
    """True when fingertip is above its PIP joint (finger extended)."""
    return lm[tip].y < lm[pip].y


# ------------------------------------------------------------------ #
# Smoothing filter (exponential moving average)
# ------------------------------------------------------------------ #
class ExponentialSmoother:
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self._val = None

    def update(self, new_val):
        if self._val is None:
            self._val = new_val
        else:
            if isinstance(new_val, (tuple, list)):
                self._val = tuple(
                    self.alpha * n + (1 - self.alpha) * o
                    for n, o in zip(new_val, self._val)
                )
            else:
                self._val = self.alpha * new_val + (1 - self.alpha) * self._val
        return self._val

    def reset(self):
        self._val = None


# ------------------------------------------------------------------ #
# Gesture cooldown tracker
# ------------------------------------------------------------------ #
class CooldownTracker:
    def __init__(self):
        self._last: dict[str, float] = {}

    def ready(self, gesture: str, cooldown_ms: int) -> bool:
        now = time.time() * 1000
        last = self._last.get(gesture, 0)
        if now - last >= cooldown_ms:
            self._last[gesture] = now
            return True
        return False

    def force(self, gesture: str):
        self._last[gesture] = time.time() * 1000


# ------------------------------------------------------------------ #
# Main Hand Tracker
# ------------------------------------------------------------------ #
class HandTracker:
    """
    Runs in a dedicated thread.
    Reads frames from a shared queue, processes them via MediaPipe,
    determines gestures, and writes results to `state`.
    """

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._smoother = ExponentialSmoother(alpha=0.3)
        self._cursor_smoother = ExponentialSmoother(alpha=0.25)
        self._cooldown = CooldownTracker()

        # Drag state
        self._drag_active = False
        self._drag_label = "DRAG"
        self._pinch_start_time = None
        self._pinch_active = False
        self._selection_candidate = False
        self._last_index_px = 0
        self._last_index_py = 0

        # Double-click detection
        self._last_pinch_time = 0.0
        self._double_click_window = 0.4  # seconds

        # Scroll / swipe tracking
        self._prev_2finger_y: float | None = None
        self._scroll_mode_active = False
        self._scroll_anchor_y: float | None = None
        self._scroll_anchor_time: float | None = None
        self._prev_3finger_x: float | None = None
        self._three_swipe_start_x: float | None = None
        self._three_swipe_armed = True
        self._prev_hand_y: float | None = None
        self._four_task_armed = True
        self._four_task_pose_since: float | None = None

        # Zoom tracking
        self._prev_pinch_dist: float | None = None
        self._zoom_accum = 0.0

        # MediaPipe setup
        if MEDIAPIPE_AVAILABLE:
            self._mp_hands = mp.solutions.hands
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.6,
            )
            self._mp_draw = mp.solutions.drawing_utils
        else:
            log.warning("MediaPipe not available - hand tracking disabled.")

    # ---------------------------------------------------------- #
    # Thread control
    # ---------------------------------------------------------- #
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="HandTracker")
        self._thread.start()
        log.info("HandTracker started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._release_drag()
        self._reset_pinch()
        log.info("HandTracker stopped")

    # ---------------------------------------------------------- #
    # Main loop
    # ---------------------------------------------------------- #
    def _run(self):
        # The camera thread puts frames into CameraCapture.frame_queue
        # We import here to avoid circular imports
        try:
            from .camera import camera_capture
        except ImportError:
            from camera import camera_capture

        while self._running and state.running:
            try:
                frame = camera_capture.get_frame(timeout=0.05)
                if frame is None:
                    continue
                t0 = time.perf_counter()
                self._process_frame(frame)
                latency = (time.perf_counter() - t0) * 1000
                state.update(latency_ms=round(latency, 1))
            except Exception as e:
                log.error(f"HandTracker error: {e}")

    # ---------------------------------------------------------- #
    # Frame processing
    # ---------------------------------------------------------- #
    def _process_frame(self, frame: np.ndarray):
        if not MEDIAPIPE_AVAILABLE or not config.gestures_enabled:
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True

        overlay = frame.copy()

        if results.multi_hand_landmarks:
            lm_list = results.multi_hand_landmarks[0].landmark

            # Draw skeleton on overlay
            self._mp_draw.draw_landmarks(
                overlay,
                results.multi_hand_landmarks[0],
                self._mp_hands.HAND_CONNECTIONS,
            )

            # Move cursor
            self._update_cursor(lm_list, overlay)

            # Detect gestures
            if config.gestures_enabled:
                gesture = self._detect_gesture(lm_list, overlay)
                state.update(
                    hand_detected=True,
                    active_gesture=gesture,
                )
            state.update(hand_detected=True)
        else:
            state.update(hand_detected=False, active_gesture=Gesture.NONE)
            self._smoother.reset()
            self._release_drag()
            self._reset_pinch()
            self._prev_2finger_y = None
            self._scroll_mode_active = False
            self._scroll_anchor_y = None
            self._scroll_anchor_time = None
            self._prev_3finger_x = None
            self._three_swipe_start_x = None
            self._three_swipe_armed = True
            self._four_task_armed = True
            self._four_task_pose_since = None
            self._prev_pinch_dist = None

        state.update(overlay_frame=overlay)

    # ---------------------------------------------------------- #
    # Cursor movement
    # ---------------------------------------------------------- #
    def _update_cursor(self, lm, overlay):
        raw_x = lm[INDEX_TIP].x
        raw_y = lm[INDEX_TIP].y

        # Map from calibrated sub-region to full screen
        nx = (raw_x - config.map_x_min) / max(config.map_x_max - config.map_x_min, 0.01)
        ny = (raw_y - config.map_y_min) / max(config.map_y_max - config.map_y_min, 0.01)
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))

        # Smooth finger position
        sx, sy = self._smoother.update((nx, ny))

        # Target screen pixel
        tx = int(sx * config.screen_width * config.cursor_sensitivity)
        ty = int(sy * config.screen_height * config.cursor_sensitivity)
        tx = max(0, min(config.screen_width - 1, tx))
        ty = max(0, min(config.screen_height - 1, ty))

        # Dead zone
        cx, cy = state.cursor_pos
        delta = math.hypot(tx - cx, ty - cy)
        
        # Adaptive cursor smoothing based on speed (delta displacement)
        base_smoothing = getattr(config, "cursor_smoothing", 0.25)
        if delta < 15:
            # Precise mode: extra smoothing (lower alpha)
            adaptive_alpha = max(0.08, base_smoothing * 0.5)
        elif delta > 80:
            # Speed mode: minimal smoothing (higher alpha) to reduce latency
            adaptive_alpha = min(0.75, base_smoothing * 2.2)
        else:
            # Intermediate dynamic interpolation
            t = (delta - 15) / (80 - 15)
            adaptive_alpha = max(0.08, min(0.75, base_smoothing * (0.5 + t * 1.7)))
        self._cursor_smoother.alpha = adaptive_alpha

        if delta < config.dead_zone_radius:
            return  # Skip tiny jitter

        # Acceleration
        if config.acceleration_enabled and delta > 20:
            factor = config.acceleration_factor
            tx = int(cx + (tx - cx) * factor)
            ty = int(cy + (ty - cy) * factor)
            tx = max(0, min(config.screen_width - 1, tx))
            ty = max(0, min(config.screen_height - 1, ty))

        # Smooth cursor
        final = self._cursor_smoother.update((tx, ty))
        fx, fy = int(final[0]), int(final[1])

        state.update(cursor_pos=(fx, fy), finger_pos=(raw_x, raw_y))

        # Move mouse (via controller imported from mouse_controller)
        try:
            try:
                from .mouse_controller import mouse_ctrl
            except ImportError:
                from mouse_controller import mouse_ctrl
            mouse_ctrl.move(fx, fy)
        except Exception:
            pass

        # Draw fingertip on overlay
        h, w = overlay.shape[:2]
        px, py = int(raw_x * w), int(raw_y * h)
        self._last_index_px = px
        self._last_index_py = py
        cv2.circle(overlay, (px, py), 10, (0, 255, 100), -1)
        cv2.circle(overlay, (px, py), 14, (255, 255, 255), 2)

    def _detect_gesture(self, lm, overlay) -> str:
        thumb_idx_dist = _dist(lm, THUMB_TIP, INDEX_TIP)
        idx_mid_dist   = _dist(lm, INDEX_TIP, MIDDLE_TIP)

        fingers_up = [
            _finger_up(lm, INDEX_TIP, INDEX_PIP),
            _finger_up(lm, MIDDLE_TIP, MIDDLE_PIP),
            _finger_up(lm, RING_TIP, RING_PIP),
            _finger_up(lm, PINKY_TIP, PINKY_PIP),
        ]
        n_up = sum(fingers_up)
        h, w = overlay.shape[:2]

        two_finger_pose = fingers_up[0] and fingers_up[1] and not fingers_up[2] and not fingers_up[3]
        mid_y = (lm[INDEX_TIP].y + lm[MIDDLE_TIP].y) / 2

        # ---- Scroll mode: index + middle held together ----
        if two_finger_pose:
            join_threshold = getattr(config, "scroll_join_threshold", 0.065)
            release_threshold = getattr(config, "scroll_release_threshold", 0.09)

            if not self._scroll_mode_active and idx_mid_dist <= join_threshold:
                self._scroll_mode_active = True
                self._scroll_anchor_y = mid_y
                self._scroll_anchor_time = time.perf_counter()
                self._draw_gesture_label(overlay, "SCROLL MODE", (100, 200, 255))
                return Gesture.SCROLL_MODE

            if self._scroll_mode_active:
                if idx_mid_dist >= release_threshold:
                    self._scroll_mode_active = False
                    self._scroll_anchor_y = None
                    self._scroll_anchor_time = None
                    self._prev_2finger_y = None
                    return Gesture.NONE

                if self._scroll_anchor_y is None:
                    self._scroll_anchor_y = mid_y
                if self._scroll_anchor_time is None:
                    self._scroll_anchor_time = time.perf_counter()

                dy = mid_y - self._scroll_anchor_y
                now = time.perf_counter()
                dt = max(now - self._scroll_anchor_time, 0.001)
                threshold = getattr(config, "scroll_motion_threshold", 0.004)
                cooldown_ms = getattr(config, "scroll_cooldown_ms", 12)
                multiplier = getattr(config, "scroll_motion_multiplier", 220.0)
                speed_multiplier = getattr(config, "scroll_speed_multiplier", 12.0)
                max_units = getattr(config, "scroll_max_units", 28)
                if abs(dy) > threshold:
                    g = Gesture.TWO_SCROLL_DN if dy > 0 else Gesture.TWO_SCROLL_UP
                    speed = abs(dy) / dt
                    speed_boost = 1.0 + min(speed * speed_multiplier, 5.0)
                    scroll_units = max(1, min(max_units, int(abs(dy) * multiplier * speed_boost)))
                    if self._cooldown.ready(g, cooldown_ms):
                        self._dispatch(g, overlay, lm, w, h, amount=scroll_units)
                        self._scroll_anchor_y = mid_y
                        self._scroll_anchor_time = now
                        return g

                self._draw_gesture_label(overlay, "SCROLL MODE", (100, 200, 255))
                return Gesture.SCROLL_MODE
        else:
            self._scroll_mode_active = False
            self._scroll_anchor_y = None
            self._scroll_anchor_time = None
            self._prev_2finger_y = None

        # ---- Pinch (index + thumb) ----
        pinch_threshold = getattr(config, "click_threshold", 0.045)
        release_threshold = max(
            getattr(config, "click_release_threshold", 0.065),
            pinch_threshold + 0.015,
        )
        click_min_hold = getattr(config, "click_min_hold_ms", 35) / 1000
        click_cooldown = getattr(config, "click_cooldown_ms", 140)

        if not self._pinch_active and thumb_idx_dist <= pinch_threshold:
            now = time.time()
            self._pinch_active = True
            self._pinch_start_time = now
            self._selection_candidate = now - self._last_pinch_time < self._double_click_window
            self._draw_gesture_label(overlay, "CLICK READY", (0, 255, 100))
            return Gesture.NONE

        if self._pinch_active:
            now = time.time()
            if self._pinch_start_time is None:
                self._pinch_start_time = now
            pinch_duration = now - self._pinch_start_time

            if self._drag_active:
                if thumb_idx_dist >= release_threshold:
                    self._release_drag()
                    self._reset_pinch()
                    return Gesture.NONE
                self._draw_gesture_label(overlay, self._drag_label, (0, 200, 255))
                # Draw solid active drag outline around fingertip
                px, py = self._last_index_px, self._last_index_py
                drag_color = (0, 165, 255) if self._drag_label == "SELECT" else (255, 165, 0)
                cv2.circle(overlay, (px, py), 22, drag_color, 2, cv2.LINE_AA)
                return Gesture.SELECT_HOLD if self._drag_label == "SELECT" else Gesture.PINCH_HOLD

            if thumb_idx_dist >= release_threshold:
                if pinch_duration >= click_min_hold and self._cooldown.ready(Gesture.PINCH, click_cooldown):
                    if now - self._last_pinch_time < self._double_click_window:
                        self._dispatch(Gesture.DOUBLE_PINCH, overlay, lm, w, h)
                        gesture = Gesture.DOUBLE_PINCH
                    else:
                        self._dispatch(Gesture.PINCH, overlay, lm, w, h)
                        gesture = Gesture.PINCH
                    self._last_pinch_time = now
                    self._reset_pinch()
                    return gesture

                self._reset_pinch()
                return Gesture.NONE

            # A double-pinch hold mirrors touchpad double-tap-and-drag
            # selection. On an empty desktop/folder area it creates the
            # rectangle selection box; over an item it drags the item.
            selection_hold = getattr(config, "selection_hold_ms", 180) / 1000
            if self._selection_candidate and pinch_duration >= selection_hold:
                if self._custom_action(Gesture.SELECT_HOLD) != "Drag / select":
                    self._dispatch(Gesture.SELECT_HOLD, overlay, lm, w, h)
                    self._reset_pinch()
                    return Gesture.SELECT_HOLD
                self._start_drag("SELECT")
                self._draw_gesture_label(overlay, "SELECT", (0, 200, 255))
                return Gesture.SELECT_HOLD

            # A longer normal hold remains regular drag.
            if pinch_duration >= config.drag_hold_ms / 1000:
                if self._custom_action(Gesture.PINCH_HOLD) != "Drag / select":
                    self._dispatch(Gesture.PINCH_HOLD, overlay, lm, w, h)
                    self._reset_pinch()
                    return Gesture.PINCH_HOLD
                self._start_drag("DRAG")
                self._draw_gesture_label(overlay, "DRAG", (0, 200, 255))
                return Gesture.PINCH_HOLD

            # Draw visual hold progress ring around index finger tip before activation
            target_time = selection_hold if self._selection_candidate else (config.drag_hold_ms / 1000)
            progress = min(1.0, pinch_duration / max(target_time, 0.01))
            if progress < 1.0:
                px, py = self._last_index_px, self._last_index_py
                progress_color = (0, 255, 255) if self._selection_candidate else (0, 255, 100)
                cv2.ellipse(
                    overlay,
                    (px, py),
                    (22, 22),
                    -90,
                    0,
                    int(progress * 360),
                    progress_color,
                    3,
                    cv2.LINE_AA
                )

            label = "HOLD TO SELECT" if self._selection_candidate else "CLICK READY"
            self._draw_gesture_label(overlay, label, (0, 255, 100))
            return Gesture.NONE

        # ---- 3-finger swipe (desktop switch) ----
        if all(fingers_up[:3]) and not fingers_up[3]:
            mid_x = (lm[INDEX_TIP].x + lm[MIDDLE_TIP].x + lm[RING_TIP].x) / 3
            if self._three_swipe_start_x is None:
                self._three_swipe_start_x = mid_x

            dx = mid_x - self._three_swipe_start_x
            if self._three_swipe_armed and abs(dx) > 0.12:
                g = Gesture.THREE_SWIPE_R if dx > 0 else Gesture.THREE_SWIPE_L
                if self._cooldown.ready(g, 1200):
                    self._dispatch(g, overlay, lm, w, h)
                    self._three_swipe_armed = False
                    self._three_swipe_start_x = mid_x
                    return g
            self._prev_3finger_x = mid_x
        else:
            self._prev_3finger_x = None
            self._three_swipe_start_x = None
            self._three_swipe_armed = True

        # ---- 4-finger spread -> task view ----
        if n_up >= 4:
            now = time.time()
            if self._four_task_pose_since is None:
                self._four_task_pose_since = now

            pose_held = now - self._four_task_pose_since >= 1.0
            if self._four_task_armed and pose_held and self._cooldown.ready(Gesture.FOUR_TASK, 2500):
                self._dispatch(Gesture.FOUR_TASK, overlay, lm, w, h)
                self._four_task_armed = False
                return Gesture.FOUR_TASK
        else:
            self._four_task_armed = True
            self._four_task_pose_since = None

        # ---- Zoom (thumb + index spread/close) ----
        if n_up == 0:  # fist-like but measuring spread
            current_dist = _dist(lm, THUMB_TIP, INDEX_TIP)
            if self._prev_pinch_dist is not None:
                delta = current_dist - self._prev_pinch_dist
                self._zoom_accum += delta
                if abs(self._zoom_accum) > 0.03:
                    g = Gesture.ZOOM_IN if self._zoom_accum > 0 else Gesture.ZOOM_OUT
                    if self._cooldown.ready(g, 200):
                        self._dispatch(g, overlay, lm, w, h)
                    self._zoom_accum = 0.0
            self._prev_pinch_dist = current_dist
        else:
            self._prev_pinch_dist = None
            self._zoom_accum = 0.0

        # ---- Fist -> minimize ----
        if n_up == 0 and self._cooldown.ready(Gesture.FIST, 1200):
            pass  # Fist held - used as modifier, not standalone

        # ---- Open palm -> maximize ----
        if n_up == 4 and self._cooldown.ready(Gesture.OPEN_PALM, 1200):
            pass  # Used in combination

        return Gesture.NONE

    # ---------------------------------------------------------- #
    # Dispatch gesture to action executor
    # ---------------------------------------------------------- #
    def _start_drag(self, label: str):
        if self._drag_active:
            return
        try:
            try:
                from .mouse_controller import mouse_ctrl
            except ImportError:
                from mouse_controller import mouse_ctrl
            mouse_ctrl.press()
        except Exception as e:
            log.error(f"Drag start error: {e}")
            return
        self._drag_active = True
        self._drag_label = label
        log.debug(f"{label.title()} drag started")

    def _release_drag(self):
        if not self._drag_active:
            return
        try:
            try:
                from .mouse_controller import mouse_ctrl
            except ImportError:
                from mouse_controller import mouse_ctrl
            mouse_ctrl.release()
        except Exception as e:
            log.error(f"Drag release error: {e}")
        self._drag_active = False
        self._drag_label = "DRAG"
        log.debug("Drag released")

    def _reset_pinch(self):
        self._pinch_active = False
        self._pinch_start_time = None
        self._selection_candidate = False

    def _dispatch(self, gesture: str, overlay, lm, w: int, h: int, amount: int | None = None):
        label_map = {
            Gesture.PINCH:         ("CLICK", (0, 255, 100)),
            Gesture.DOUBLE_PINCH:  ("DBL CLICK", (0, 255, 255)),
            Gesture.PINCH_HOLD:    ("HOLD", (0, 200, 255)),
            Gesture.SELECT_HOLD:   ("SELECT HOLD", (0, 200, 255)),
            Gesture.RIGHT_CLICK:   ("RIGHT CLICK", (255, 100, 0)),
            Gesture.TWO_SCROLL_UP: ("SCROLL UP", (100, 200, 255)),
            Gesture.TWO_SCROLL_DN: ("SCROLL DOWN", (100, 200, 255)),
            Gesture.THREE_SWIPE_R: ("DESK RIGHT", (255, 200, 0)),
            Gesture.THREE_SWIPE_L: ("DESK LEFT", (255, 200, 0)),
            Gesture.FOUR_TASK:     ("TASK VIEW", (200, 100, 255)),
            Gesture.ZOOM_IN:       ("ZOOM IN", (100, 255, 200)),
            Gesture.ZOOM_OUT:      ("ZOOM OUT", (100, 255, 200)),
        }
        label, color = label_map.get(gesture, (gesture.upper(), (255, 255, 255)))
        self._draw_gesture_label(overlay, label, color)

        # Execute in executor
        try:
            try:
                from .action_executor import executor
            except ImportError:
                from action_executor import executor
            if amount is None:
                executor.execute_gesture(gesture)
            else:
                executor.execute_gesture(gesture, amount=amount)
        except Exception as e:
            log.error(f"Gesture dispatch error: {e}")

        state.update(active_gesture=gesture, gesture_confidence=0.9)
        log.debug(f"Gesture: {gesture}")

    def _custom_action(self, gesture: str) -> str:
        mapping = getattr(config, "custom_gesture_mapping", None) or {}
        return mapping.get(gesture, "Drag / select")

    def _draw_gesture_label(self, overlay, text: str, color):
        h, w = overlay.shape[:2]
        cv2.rectangle(overlay, (10, h - 60), (280, h - 20), (0, 0, 0), -1)
        cv2.putText(
            overlay, text, (20, h - 30),
            cv2.FONT_HERSHEY_DUPLEX, 0.9, color, 2, cv2.LINE_AA
        )


# Singleton
hand_tracker = HandTracker()


def main():
    """Run camera + hand tracking when this file is executed directly."""
    state.reset_runtime()
    try:
        from .camera import camera_capture
    except ImportError:
        from camera import camera_capture

    window_name = "X75 MotionOS Preview"
    print("Starting hand tracking...")
    print(f"Using camera index: {config.camera_index}")
    print("Press q in the preview window to quit.")

    camera_capture.start()
    if not state.get("camera_running"):
        available = camera_capture.list_cameras()
        print(f"Camera failed to start. Available camera indices: {available}")
        print("Try changing camera_index in config.py or settings.json.")
        return 1

    hand_tracker.start()
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while state.running:
            frame = state.get("overlay_frame")
            if frame is None:
                frame = state.get("frame")

            if frame is not None:
                display = frame.copy()
                gesture = state.get("active_gesture") or Gesture.NONE
                fps = state.get("fps") or 0.0
                latency = state.get("latency_ms") or 0.0
                cv2.putText(display, f"Gesture: {gesture}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 220, 80), 2, cv2.LINE_AA)
                cv2.putText(display, f"FPS: {fps:.1f}  Latency: {latency:.1f} ms", (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(display, "Press q to quit", (12, display.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 2, cv2.LINE_AA)
                cv2.imshow(window_name, display)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            time.sleep(0.005)
    except KeyboardInterrupt:
        print("Stopping hand tracking...")
    finally:
        state.running = False
        hand_tracker.stop()
        camera_capture.stop()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
