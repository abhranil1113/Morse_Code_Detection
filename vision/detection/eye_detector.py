import numpy as np
from typing import Dict, Tuple, Optional


class EyeDetector:
    """Calculates Eye Aspect Ratio (EAR) and bounding box boundaries from landmarks."""

    @staticmethod
    def calculate_ear(eye_landmarks: np.ndarray) -> float:
        """
        Calculates Eye Aspect Ratio (EAR) based on Soukupová and Čech (2016):
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
        """
        if len(eye_landmarks) < 6:
            return 0.0

        p1, p2, p3, p4, p5, p6 = eye_landmarks[:6]

        # Vertical distances (p2 with p6, p3 with p5)
        v1 = np.linalg.norm(p2 - p6)
        v2 = np.linalg.norm(p3 - p5)

        # Horizontal distance
        h = np.linalg.norm(p1 - p4)

        if h < 1e-6:
            return 0.0

        ear = (v1 + v2) / (2.0 * h)
        return float(ear)

    @classmethod
    def get_eye_metrics(cls, landmarks_dict: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Compute left, right, and average EAR."""
        left_eye = landmarks_dict.get("left_eye")
        right_eye = landmarks_dict.get("right_eye")

        if left_eye is None or right_eye is None:
            return {"left_ear": 0.0, "right_ear": 0.0, "avg_ear": 0.0}

        left_ear = cls.calculate_ear(left_eye)
        right_ear = cls.calculate_ear(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0

        return {
            "left_ear": left_ear,
            "right_ear": right_ear,
            "avg_ear": avg_ear
        }

    @staticmethod
    def get_eye_bounding_box(eye_pts: np.ndarray, padding: int = 10, img_shape: Tuple[int, int] = (480, 640)) -> Tuple[int, int, int, int]:
        """Calculate padded bounding box [x_min, y_min, x_max, y_max]."""
        h_max, w_max = img_shape
        x_min = max(0, int(np.min(eye_pts[:, 0])) - padding)
        y_min = max(0, int(np.min(eye_pts[:, 1])) - padding)
        x_max = min(w_max, int(np.max(eye_pts[:, 0])) + padding)
        y_max = min(h_max, int(np.max(eye_pts[:, 1])) + padding)
        return x_min, y_min, x_max, y_max
