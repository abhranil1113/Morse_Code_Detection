import cv2
import numpy as np
from typing import Tuple, Optional
from vision.detection.eye_detector import EyeDetector


class EyeCropper:
    """Crops and normalizes eye regions to standard dimensions for feature extraction & ML."""

    def __init__(self, target_size: Tuple[int, int] = (32, 32)):
        self.target_size = target_size

    def crop_eye(
        self,
        frame: np.ndarray,
        eye_pts: np.ndarray,
        padding: int = 8,
        face_scale: Optional[float] = None
    ) -> Optional[np.ndarray]:
        """Crop an eye region using adaptive ROI, convert to grayscale, histogram equalize, and resize."""
        if frame is None or not hasattr(frame, "shape") or frame.size == 0:
            return None

        if eye_pts is None or len(eye_pts) == 0:
            return None

        h, w = frame.shape[:2]
        bbox = EyeDetector.get_adaptive_eye_bounding_box(
            eye_pts,
            face_scale=face_scale,
            padding_ratio=max(0.25, float(padding) / 25.0),
            img_shape=(h, w)
        )
        if bbox is None:
            return None

        x_min, y_min, x_max, y_max = bbox

        crop = frame[y_min:y_max, x_min:x_max]
        if crop.size == 0 or crop.shape[0] < 4 or crop.shape[1] < 4:
            return None

        # Convert to Grayscale
        if len(crop.shape) == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop

        # Histogram equalization for lighting invariance
        equalized = cv2.equalizeHist(gray)

        # Resize to fixed standard shape
        resized = cv2.resize(equalized, self.target_size, interpolation=cv2.INTER_AREA)
        return resized
