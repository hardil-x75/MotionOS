# ============================================================
# run_hand_control.py - Full launcher for hands-free control
# ============================================================

import threading
import time
import platform
from importlib.util import find_spec

import cv2

from hands_free_control.action_executor import executor
from hands_free_control.camera import camera_capture
from hands_free_control.config import config, state
from hands_free_control.hand_tracker import hand_tracker
from hands_free_control import __product_name__
from hands_free_control.logger import log


WINDOW_NAME = f"{__product_name__} Preview"


def _show_launch_error(title: str, message: str):
    if platform.system() == "Windows":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
            return
        except Exception:
            pass
    print(f"{title}: {message}")


def _sync_screen_size():
    """Use the real display size for cursor mapping when pyautogui is available."""
    try:
        import pyautogui

        width, height = pyautogui.size()
        if width > 0 and height > 0:
            config.screen_width = int(width)
            config.screen_height = int(height)
            state.update(cursor_pos=(config.screen_width // 2, config.screen_height // 2))
            log.info(f"Detected screen size: {config.screen_width}x{config.screen_height}")
    except Exception as e:
        log.warning(f"Could not detect screen size automatically: {e}")


class VoiceListener:
    """Background speech listener that sends recognized text to ActionExecutor."""

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._recognizer = None
        self._microphone = None
        self._available = False
        self._unavailable_reason = ""

        try:
            import speech_recognition as sr
        except ImportError:
            self._sr = None
            self._unavailable_reason = "SpeechRecognition is not installed"
            return

        self._sr = sr
        self._recognizer = sr.Recognizer()
        self._available = True

    @property
    def available(self):
        return self._available

    @property
    def unavailable_reason(self):
        return self._unavailable_reason

    def start(self):
        if not config.voice_enabled:
            print("Voice listener disabled in config.py.")
            return
        if not self._available:
            print(f"Voice listener unavailable: {self._unavailable_reason}")
            return
        if self._running:
            return

        self._running = True
        state.update(voice_running=True)
        self._thread = threading.Thread(target=self._run, daemon=True, name="VoiceListener")
        self._thread.start()
        log.info("VoiceListener started")

    def stop(self):
        self._running = False
        state.update(voice_running=False, listening=False)
        if self._thread:
            self._thread.join(timeout=2)
        log.info("VoiceListener stopped")

    def _open_microphone(self):
        try:
            return self._sr.Microphone(device_index=config.microphone_index)
        except Exception as first_error:
            log.warning(f"Configured microphone failed: {first_error}. Trying default microphone.")
            try:
                return self._sr.Microphone()
            except Exception as second_error:
                self._unavailable_reason = str(second_error)
                log.error(f"Microphone unavailable: {second_error}")
                return None

    def _recognize(self, audio):
        engine = config.voice_engine.lower().strip()
        if engine == "whisper" and find_spec("whisper") is not None:
            return self._recognizer.recognize_whisper(audio)
        if engine == "vosk" and find_spec("vosk") is not None:
            return self._recognizer.recognize_vosk(audio)
        if engine != "google":
            log.warning(f"Voice engine '{engine}' is unavailable; falling back to google")
        return self._recognizer.recognize_google(audio)

    def _run(self):
        mic = self._open_microphone()
        if mic is None:
            print(f"Voice listener unavailable: {self._unavailable_reason}")
            state.update(voice_running=False, listening=False)
            return

        try:
            with mic as source:
                print("Calibrating microphone noise... please stay quiet for a moment.")
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Voice listener ready.")

                while self._running and state.running:
                    try:
                        state.update(listening=True, voice_active=True)
                        audio = self._recognizer.listen(
                            source,
                            timeout=config.voice_timeout,
                            phrase_time_limit=config.voice_phrase_limit,
                        )
                        state.update(listening=False)

                        command = self._recognize(audio).strip()
                        if not command:
                            continue

                        if config.wake_word_mode:
                            lower = command.lower()
                            wake = config.wake_word.lower().strip()
                            if not lower.startswith(wake):
                                log.debug(f"Ignored voice command without wake word: {command}")
                                continue
                            command = command[len(wake):].strip()

                        print(f"Voice command: {command}")
                        executor.execute_voice(command)
                    except self._sr.WaitTimeoutError:
                        state.update(listening=False)
                    except self._sr.UnknownValueError:
                        state.update(listening=False)
                        log.debug("Could not understand audio")
                    except Exception as e:
                        state.update(listening=False)
                        log.error(f"Voice listener error: {e}")
                        time.sleep(0.5)
        finally:
            state.update(voice_running=False, listening=False, voice_active=False)


voice_listener = VoiceListener()


def _draw_status(frame):
    """Draw lightweight runtime status on the preview frame."""
    hand_status = "Hand: yes" if state.get("hand_detected") else "Hand: no"
    voice_status = "Voice: on" if state.get("voice_running") else "Voice: off"
    listen_status = "listening" if state.get("listening") else "idle"
    gesture = state.get("active_gesture") or "none"
    fps = state.get("fps") or 0.0
    latency = state.get("latency_ms") or 0.0
    last_command = state.get("last_command") or ""

    cv2.putText(frame, hand_status, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 120), 2, cv2.LINE_AA)
    cv2.putText(frame, f"{voice_status} ({listen_status})", (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 220, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"Gesture: {gesture}", (12, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 220, 80), 2, cv2.LINE_AA)
    cv2.putText(frame, f"FPS: {fps:.1f}  Latency: {latency:.1f} ms", (12, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    if last_command:
        cv2.putText(frame, last_command[-55:], (12, frame.shape[0] - 48), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 2, cv2.LINE_AA)
    cv2.putText(frame, "Press q to quit", (12, frame.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 2, cv2.LINE_AA)
    return frame


def main():
    state.reset_runtime()
    _sync_screen_size()

    print(f"Starting {__product_name__}...")
    print(f"Camera index: {config.camera_index}")
    print(f"Screen size: {config.screen_width}x{config.screen_height}")
    print(f"Voice enabled: {config.voice_enabled} ({config.voice_engine})")
    print("Press q in the preview window to quit.")

    camera_capture.start()
    if not state.get("camera_running"):
        available = camera_capture.list_cameras()
        message = (
            f"Camera {config.camera_index} failed to start.\n"
            f"Available camera indices: {available}\n\n"
            "Close apps that use the camera or choose another camera index in settings."
        )
        print(message)
        _show_launch_error("Camera unavailable", message)
        return 1

    hand_tracker.start()
    voice_listener.start()
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    try:
        while state.running:
            frame = state.get("overlay_frame")
            if frame is None:
                frame = state.get("frame")

            if frame is not None:
                cv2.imshow(WINDOW_NAME, _draw_status(frame.copy()))

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            time.sleep(0.005)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        state.running = False
        voice_listener.stop()
        hand_tracker.stop()
        camera_capture.stop()
        cv2.destroyAllWindows()
        log.info(f"{__product_name__} stopped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
