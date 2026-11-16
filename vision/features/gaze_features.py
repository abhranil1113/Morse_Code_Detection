import numpy as np
from typing import Dict, Tuple, Optional


class GazeFeatureExtractor:
    """Extracts gaze direction features based on iris centers relative to eye corners."""

    @staticmethod
    def compute_iris_center(iris_landmarks: np.ndarray) -> np.ndarray:
        """Returns the mean coordinate of the 4 iris landmarks."""
        if iris_landmarks is None or len(iris_landmarks) == 0:
            return np.array([0.0, 0.0])
        return np.mean(iris_landmarks, axis=0)

    @classmethod
    def get_gaze_ratio(
        cls,
        eye_landmarks: np.ndarray,
        iris_landmarks: Optional[np.ndarray]
    ) -> float:
        """
        Calculates horizontal ratio of iris between inner and outer eye corners:
        Ratio < 0.38 => Looking Right (or user's right)
        Ratio > 0.62 => Looking Left
        Ratio ~ 0.50 => Looking Center
        """
        if eye_landmarks is None or len(eye_landmarks) < 6:
            return 0.5

        p_outer = eye_landmarks[0]
        p_inner = eye_landmarks[3]

        if iris_landmarks is not None and len(iris_landmarks) > 0:
            iris_center = cls.compute_iris_center(iris_landmarks)
            dist_outer = np.linalg.norm(iris_center - p_outer)
            dist_inner = np.linalg.norm(iris_center - p_inner)
            total_dist = dist_outer + dist_inner
            if total_dist > 1e-6:
                return float(dist_outer / total_dist)

        return 0.5

    @classmethod
    def extract_full_feature_vector(
        cls,
        landmarks_dict: Dict[str, np.ndarray],
        hog_left: np.ndarray,
        hog_right: np.ndarray
    ) -> np.ndarray:
        """
        Combines EAR (2), Gaze Ratios (2), and HOG descriptors into a single compact feature vector.
        """
        from vision.detection.eye_detector import EyeDetector

        left_eye = landmarks_dict.get("left_eye")
        right_eye = landmarks_dict.get("right_eye")
        left_iris = landmarks_dict.get("left_iris")
        right_iris = landmarks_dict.get("right_iris")

        left_ear = EyeDetector.calculate_ear(left_eye) if left_eye is not None else 0.0
        right_ear = EyeDetector.calculate_ear(right_eye) if right_eye is not None else 0.0

        left_ratio = cls.get_gaze_ratio(left_eye, left_iris)
        right_ratio = cls.get_gaze_ratio(right_eye, right_iris)

        geometric_features = np.array([left_ear, right_ear, left_ratio, right_ratio], dtype=np.float32)
        return np.concatenate([geometric_features, hog_left, hog_right])
