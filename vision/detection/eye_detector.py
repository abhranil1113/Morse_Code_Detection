import numpy as np
from typing import Dict, Tuple, Optional, Any


import numpy as np
from typing import Dict, Tuple, Optional, Any


class EyeDetector:
    """
    Calculates Eye Aspect Ratio (EAR), adaptive bounding boxes, and independent
    eye visibility states (VISIBLE, PARTIALLY_VISIBLE, OCCLUDED, OUT_OF_FRAME, TRACKING_LOST, UNKNOWN).
    """

    @staticmethod
    def validate_eye_landmarks(
        eye_landmarks: Any,
        img_shape: Optional[Tuple[int, int]] = None,
        min_horizontal_span: float = 2.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates landmark array for shape, finiteness, dimension bounds, and non-degeneracy.
        Returns:
            (is_valid, failure_reason)
        """
        if eye_landmarks is None:
            return False, "LANDMARKS_NONE"

        if not isinstance(eye_landmarks, np.ndarray):
            return False, "NOT_NUMPY_ARRAY"

        if eye_landmarks.ndim != 2 or eye_landmarks.shape[0] < 6 or eye_landmarks.shape[1] < 2:
            return False, f"MALFORMED_SHAPE_{eye_landmarks.shape}"

        if not np.isfinite(eye_landmarks[:6, :2]).all():
            return False, "NON_FINITE_VALUES"

        if img_shape is not None:
            h, w = img_shape[:2]
            margin = 30.0  # Allow modest landmark projection outside visible frame
            xs = eye_landmarks[:6, 0]
            ys = eye_landmarks[:6, 1]
            if (xs < -margin).any() or (xs > w + margin).any() or (ys < -margin).any() or (ys > h + margin).any():
                return False, "COORDINATES_OUT_OF_BOUNDS"

        # Check horizontal distance between corners p1 (index 0) and p4 (index 3)
        p1 = eye_landmarks[0, :2]
        p4 = eye_landmarks[3, :2]
        horizontal_span = float(np.linalg.norm(p1 - p4))
        if horizontal_span < min_horizontal_span:
            return False, "DEGENERATE_SPAN"

        return True, None

    @classmethod
    def calculate_ear_3d(cls, eye_landmarks_3d: np.ndarray) -> Optional[float]:
        """
        Calculates Eye Aspect Ratio in 3D metric coordinates.
        EAR_3D is geometrically invariant to head yaw, pitch, and roll rotation.
        """
        if eye_landmarks_3d is None or not isinstance(eye_landmarks_3d, np.ndarray):
            return None
        if eye_landmarks_3d.ndim != 2 or eye_landmarks_3d.shape[0] < 6 or eye_landmarks_3d.shape[1] < 3:
            return None
        if not np.isfinite(eye_landmarks_3d[:6, :3]).all():
            return None

        p1, p2, p3, p4, p5, p6 = eye_landmarks_3d[:6, :3]
        v1 = float(np.linalg.norm(p2 - p6))
        v2 = float(np.linalg.norm(p3 - p5))
        h = float(np.linalg.norm(p1 - p4))

        if h < 1e-6:
            return None

        ear = (v1 + v2) / (2.0 * h)
        if not np.isfinite(ear) or ear < 0.0 or ear > 1.5:
            return None
        return float(ear)

    @classmethod
    def calculate_ear(
        cls,
        eye_landmarks: np.ndarray,
        img_shape: Optional[Tuple[int, int]] = None,
        eye_landmarks_3d: Optional[np.ndarray] = None,
        head_yaw: Optional[float] = None
    ) -> Optional[float]:
        """
        Calculates Eye Aspect Ratio (EAR) based on Soukupová and Čech (2016):
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
        If 3D landmarks are available, uses 3D rotation-invariant metric EAR.
        Returns None if landmarks are missing, malformed, or degenerate.
        """
        # Prioritize rotation-invariant 3D EAR when available
        if eye_landmarks_3d is not None:
            ear_3d = cls.calculate_ear_3d(eye_landmarks_3d)
            if ear_3d is not None:
                return ear_3d

        is_valid, _ = cls.validate_eye_landmarks(eye_landmarks, img_shape=img_shape)
        if not is_valid:
            return None

        p1, p2, p3, p4, p5, p6 = eye_landmarks[:6, :2]

        # Vertical distances (p2 with p6, p3 with p5)
        v1 = float(np.linalg.norm(p2 - p6))
        v2 = float(np.linalg.norm(p3 - p5))

        # Horizontal distance
        h = float(np.linalg.norm(p1 - p4))

        if h < 1e-6:
            return None

        ear = (v1 + v2) / (2.0 * h)
        if not np.isfinite(ear) or ear < 0.0 or ear > 1.5:
            return None

        # Compensate for 2D perspective foreshortening if head yaw is significant
        if head_yaw is not None and abs(head_yaw) > 10.0:
            rad = np.radians(min(55.0, abs(head_yaw)))
            cos_yaw = float(np.cos(rad))
            if cos_yaw > 0.4:
                ear = ear * cos_yaw

        return float(ear)

    @classmethod
    def get_eye_metrics(
        cls,
        landmarks_dict: Dict[str, Any],
        img_shape: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Optional[float]]:
        """
        Compute left, right, and average EAR.
        Returns None for missing or invalid EAR rather than 0.0 to prevent
        detection failures from being falsely interpreted as CLOSED eyes.
        """
        if not landmarks_dict:
            return {"left_ear": None, "right_ear": None, "avg_ear": None}

        left_eye = landmarks_dict.get("left_eye")
        right_eye = landmarks_dict.get("right_eye")
        left_eye_3d = landmarks_dict.get("left_eye_3d")
        right_eye_3d = landmarks_dict.get("right_eye_3d")
        head_yaw = landmarks_dict.get("head_pose", {}).get("yaw") if isinstance(landmarks_dict.get("head_pose"), dict) else None

        left_ear = cls.calculate_ear(left_eye, img_shape=img_shape, eye_landmarks_3d=left_eye_3d, head_yaw=head_yaw)
        right_ear = cls.calculate_ear(right_eye, img_shape=img_shape, eye_landmarks_3d=right_eye_3d, head_yaw=head_yaw)

        if left_ear is not None and right_ear is not None:
            avg_ear = (left_ear + right_ear) / 2.0
        elif left_ear is not None:
            avg_ear = left_ear
        elif right_ear is not None:
            avg_ear = right_ear
        else:
            avg_ear = None

        return {
            "left_ear": left_ear,
            "right_ear": right_ear,
            "avg_ear": avg_ear
        }

    @classmethod
    def get_adaptive_eye_bounding_box(
        cls,
        eye_pts: np.ndarray,
        face_scale: Optional[float] = None,
        padding_ratio: float = 0.35,
        min_box_size: int = 24,
        img_shape: Tuple[int, int] = (480, 640)
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Calculates an adaptive, square-aspect Region of Interest (ROI) centered on the eye.
        Maintains consistent dimensions during eye closures and head turns, preventing
        aspect-ratio distortion when resized for machine learning.
        """
        is_valid, _ = cls.validate_eye_landmarks(eye_pts, img_shape=img_shape)
        if not is_valid:
            return None

        h_max, w_max = img_shape[:2]

        # Center point from eye corners p1 and p4
        p1 = eye_pts[0, :2]
        p4 = eye_pts[3, :2]
        c_x = float((p1[0] + p4[0]) / 2.0)
        c_y = float((p1[1] + p4[1]) / 2.0)

        # Baseline span between outer and inner eye corners
        horiz_span = float(np.linalg.norm(p1 - p4))

        # Use face scale (inter-eye distance or face width) if span is foreshortened
        effective_span = horiz_span
        if face_scale is not None and face_scale > 20.0:
            min_expected_span = face_scale * 0.18
            if effective_span < min_expected_span:
                effective_span = min_expected_span

        half_size = max(int(min_box_size // 2), int(effective_span * (0.50 + padding_ratio)))

        x_min = max(0, int(c_x - half_size))
        y_min = max(0, int(c_y - half_size))
        x_max = min(w_max, int(c_x + half_size))
        y_max = min(h_max, int(c_y + half_size))

        if x_max - x_min < 8 or y_max - y_min < 8:
            return None

        return x_min, y_min, x_max, y_max

    @classmethod
    def get_eye_bounding_box(
        cls,
        eye_pts: np.ndarray,
        padding: int = 10,
        img_shape: Tuple[int, int] = (480, 640)
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Calculate bounding box [x_min, y_min, x_max, y_max].
        Uses adaptive ROI with minimum padding for backward compatibility.
        """
        return cls.get_adaptive_eye_bounding_box(
            eye_pts,
            padding_ratio=max(0.20, float(padding) / 30.0),
            img_shape=img_shape
        )

    @classmethod
    def evaluate_eye_visibility(
        cls,
        eye_pts: Optional[np.ndarray],
        img_shape: Tuple[int, int] = (480, 640),
        head_yaw: float = 0.0,
        is_left_eye: bool = True
    ) -> str:
        """
        Evaluates independent eye visibility status:
        - VISIBLE: Eye is cleanly facing camera with valid geometry.
        - PARTIALLY_VISIBLE: Moderate yaw rotation or near frame edge.
        - OCCLUDED: Physically blocked by nose bridge due to strong head yaw.
        - OUT_OF_FRAME: Landmarks extend outside the camera frame boundary.
        - TRACKING_LOST: Landmark array missing or untracked.
        - UNKNOWN: Malformed or non-finite coordinates.
        """
        if eye_pts is None or not isinstance(eye_pts, np.ndarray) or len(eye_pts) == 0:
            return "TRACKING_LOST"

        if eye_pts.ndim != 2 or eye_pts.shape[0] < 6 or eye_pts.shape[1] < 2:
            return "UNKNOWN"

        if not np.isfinite(eye_pts[:6, :2]).all():
            return "UNKNOWN"

        h, w = img_shape[:2]
        xs = eye_pts[:6, 0]
        ys = eye_pts[:6, 1]

        # 1. OUT_OF_FRAME check
        if (xs < 0).any() or (xs > w).any() or (ys < 0).any() or (ys > h).any():
            return "OUT_OF_FRAME"

        # 2. Geometry check: horizontal span between p1 and p4
        p1 = eye_pts[0, :2]
        p4 = eye_pts[3, :2]
        span = float(np.linalg.norm(p1 - p4))
        if span < 3.5:
            return "OCCLUDED"

        # 3. Head Pose & Occlusion awareness
        # Positive yaw: head rotated leftward in image (left eye turned away/behind nose)
        # Negative yaw: head rotated rightward in image (right eye turned away/behind nose)
        if is_left_eye:
            # Left eye (user's right in mirrored webcam)
            if head_yaw > 32.0 or span < 5.0 and head_yaw > 20.0:
                return "OCCLUDED"
            elif head_yaw > 18.0 or xs.min() < 18 or xs.max() > w - 18:
                return "PARTIALLY_VISIBLE"
        else:
            # Right eye (user's left in mirrored webcam)
            if head_yaw < -32.0 or span < 5.0 and head_yaw < -20.0:
                return "OCCLUDED"
            elif head_yaw < -18.0 or xs.min() < 18 or xs.max() > w - 18:
                return "PARTIALLY_VISIBLE"

        # Near edge of frame without being completely out
        if xs.min() < 15 or xs.max() > w - 15 or ys.min() < 15 or ys.max() > h - 15:
            return "PARTIALLY_VISIBLE"

        return "VISIBLE"


