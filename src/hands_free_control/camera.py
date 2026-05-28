# ============================================================
# camera.py - Camera capture thread
# ============================================================

import time
import threading
import queue
import numpy as np
import cv2

try:
    from .config import config, state
    from .logger import log
except ImportError:
    from config import config, state
    from logger import log


class CameraCapture:
    """
    Dedicated thread that grabs frames from the webcam and
    exposes the latest frame via a thread-safe queue.
    """

    def __init__(self):
        self._cap: cv2.VideoCapture | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self._fps_counter = 0
        self._fps_ts = time.time()

    def start(self):
        if self._running:
            return
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        self._cap = cv2.VideoCapture(config.camera_index)
        if not self._cap.isOpened():
            log.error(f"Cannot open camera {config.camera_index}")
            self._cap.release()
            self._cap = None
            return
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
        self._cap.set(cv2.CAP_PROP_FPS, config.target_fps)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # minimize latency
        self._running = True
        state.update(camera_running=True)
        self._thread = threading.Thread(target=self._run, daemon=True, name="CameraCapture")
        self._thread.start()
        log.info(f"CameraCapture started (index={config.camera_index})")

    def stop(self):
        self._running = False
        state.update(camera_running=False)
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()
            self._cap = None
        log.info("CameraCapture stopped")

    def get_frame(self, timeout: float = 0.1) -> np.ndarray | None:
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _run(self):
        while self._running and state.running:
            ret, frame = self._cap.read()
            if not ret:
                log.warning("Camera read failed - retrying...")
                time.sleep(0.05)
                continue

            # Flip horizontally (mirror mode)
            frame = cv2.flip(frame, 1)
            state.update(frame=frame)

            # Put frame into queue (drop old if full)
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put_nowait(frame)

            # FPS calculation
            self._fps_counter += 1
            now = time.time()
            elapsed = now - self._fps_ts
            if elapsed >= 1.0:
                fps = self._fps_counter / elapsed
                state.update(fps=round(fps, 1))
                self._fps_counter = 0
                self._fps_ts = now

    def list_cameras(self) -> list[int]:
        """Probe indices 0-9 for available cameras."""
        available = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available


camera_capture = CameraCapture()


def main():
    """Run a simple camera preview when this file is executed directly."""
    state.reset_runtime()
    print("Starting camera preview...")
    print(f"Using camera index: {config.camera_index}")
    print("Press q in the preview window to quit.")

    camera_capture.start()
    if not state.get("camera_running"):
        available = camera_capture.list_cameras()
        print(f"Camera failed to start. Available camera indices: {available}")
        print("Try changing camera_index in config.py or settings.json.")
        return 1

    cv2.namedWindow("Camera Preview", cv2.WINDOW_NORMAL)

    try:
        while state.running:
            frame = state.get("frame")
            if frame is not None:
                cv2.putText(
                    frame,
                    f"Camera {config.camera_index} | FPS: {state.get('fps') or 0.0:.1f} | Press q to quit",
                    (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 120),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow("Camera Preview", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            time.sleep(0.005)
    except KeyboardInterrupt:
        print("Stopping camera preview...")
    finally:
        state.running = False
        camera_capture.stop()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
