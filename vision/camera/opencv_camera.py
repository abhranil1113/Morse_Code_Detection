import cv2
import time
import threading
from typing import Optional, Tuple
import numpy as np


class OpenCVCamera:
    """Threaded OpenCV Camera capture for smooth real-time video processing."""

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480):
        self.camera_index = camera_index
        self.width = width
        self.height = height

        self.cap: Optional[cv2.VideoCapture] = None
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None

        self.latest_frame: Optional[np.ndarray] = None
        self.lock = threading.Lock()
        self.fps: float = 0.0
        self._prev_frame_time: float = 0.0

    def is_opened(self) -> bool:
        return self.running and self.cap is not None and self.cap.isOpened()

    def start(self) -> bool:
        """Initialize the camera and start the background capture thread."""
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            # Fallback to default backend if DSHOW fails
            self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            print(f"[OpenCVCamera] Error: Cannot open webcam index {self.camera_index}")
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print(f"[OpenCVCamera] Camera {self.camera_index} started at {self.width}x{self.height}")
        return True

    def _capture_loop(self):
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            current_time = time.time()
            if self._prev_frame_time > 0:
                dt = current_time - self._prev_frame_time
                if dt > 0:
                    self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt)
            self._prev_frame_time = current_time

            # Mirror frame horizontally for natural user interaction
            frame = cv2.flip(frame, 1)

            with self.lock:
                self.latest_frame = frame

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Return the latest frame captured by the background thread."""
        with self.lock:
            if self.latest_frame is None:
                return False, None
            return True, self.latest_frame.copy()

    def stop(self):
        """Release camera resources."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
        print("[OpenCVCamera] Camera stopped.")
