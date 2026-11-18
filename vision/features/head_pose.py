import cv2
import numpy as np
from typing import Dict, Tuple, Optional, Any


class HeadPoseEstimator:
    """
    Estimates 3D head pose (yaw, pitch, roll in degrees) using facial landmarks
    and OpenCV solvePnP with anthropometric 3D facial model points.
    """

    # Canonical 3D facial model points (in mm, centered near nose bridge/tip)
    MODEL_POINTS_3D = np.array([
        (0.0, 0.0, 0.0),             # Nose tip (MediaPipe landmark index 1)
        (0.0, -330.0, -65.0),        # Chin (index 152)
        (-225.0, 170.0, -135.0),     # Left eye outer corner (index 33)
        (225.0, 170.0, -135.0),      # Right eye outer corner (index 263)
        (-150.0, -150.0, -125.0),    # Left mouth corner (index 61)
        (150.0, -150.0, -125.0)      # Right mouth corner (index 291)
    ], dtype=np.float64)

    POSE_LANDMARK_INDICES = [1, 152, 33, 263, 61, 291]

    @classmethod
    def estimate_pose(
        cls,
        all_landmarks_2d: np.ndarray,
        img_shape: Tuple[int, int] = (480, 640)
    ) -> Dict[str, float]:
        """
        Estimate head orientation angles in degrees.
        Returns:
            Dict containing:
                - 'yaw': rotation around vertical Y axis (negative = left, positive = right)
                - 'pitch': rotation around horizontal X axis (negative = down, positive = up)
                - 'roll': rotation around viewing Z axis (head tilt)
        """
        if all_landmarks_2d is None or len(all_landmarks_2d) < max(cls.POSE_LANDMARK_INDICES) + 1:
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

        try:
            h, w = img_shape[:2]
            focal_length = float(w)
            center = (float(w) / 2.0, float(h) / 2.0)

            camera_matrix = np.array([
                [focal_length, 0.0, center[0]],
                [0.0, focal_length, center[1]],
                [0.0, 0.0, 1.0]
            ], dtype=np.float64)
            dist_coeffs = np.zeros((4, 1), dtype=np.float64)

            image_points = np.array([
                all_landmarks_2d[idx, :2] for idx in cls.POSE_LANDMARK_INDICES
            ], dtype=np.float64)

            # Check finiteness
            if not np.isfinite(image_points).all():
                return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

            success, rvec, _ = cv2.solvePnP(
                cls.MODEL_POINTS_3D,
                image_points,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_EPNP
            )

            if not success:
                return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

            rmat, _ = cv2.Rodrigues(rvec)
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

            # Normalized angle outputs in degrees:
            # angles[0] is pitch, angles[1] is yaw, angles[2] is roll
            raw_pitch = float(angles[0])
            raw_yaw = float(angles[1])
            raw_roll = float(angles[2])

            # Adjust pitch baseline (RQDecomp often centers around 180 or 0)
            if raw_pitch > 90.0:
                pitch = raw_pitch - 180.0
            elif raw_pitch < -90.0:
                pitch = raw_pitch + 180.0
            else:
                pitch = raw_pitch

            yaw = round(raw_yaw, 1)
            pitch = round(pitch, 1)
            roll = round(raw_roll, 1)

            return {
                "yaw": yaw,
                "pitch": pitch,
                "roll": roll
            }
        except Exception:
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
