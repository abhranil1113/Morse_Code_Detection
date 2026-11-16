from typing import Generator, Optional
import numpy as np
from vision.camera.opencv_camera import OpenCVCamera


class CameraManager:
    """Manages camera lifecycle, fallbacks, and generator streams."""

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480):
        self.camera = OpenCVCamera(camera_index=camera_index, width=width, height=height)

    def __enter__(self):
        self.camera.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.camera.stop()

    def get_frame(self) -> Optional[np.ndarray]:
        ret, frame = self.camera.read_frame()
        return frame if ret else None

    def stream(self) -> Generator[np.ndarray, None, None]:
        while self.camera.running:
            ret, frame = self.camera.read_frame()
            if ret and frame is not None:
                yield frame
