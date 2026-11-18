import os
import time
from typing import Optional, List, Tuple, Dict, Any
import numpy as np
import cv2

from vision.detection.eye_detector import EyeDetector
from vision.features.head_pose import HeadPoseEstimator

try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False


class FaceLandmarker:
    """
    Detects facial and ocular landmarks using MediaPipe FaceMesh with Haar Cascade fallback.
    Returns structured detection validity and explicit failure reasons.
    """

    # Key landmark indices for Eye Aspect Ratio (EAR) & Iris
    LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
    LEFT_IRIS_INDICES = [468, 469, 470, 471]
    RIGHT_IRIS_INDICES = [473, 474, 475, 476]

    def __init__(self, max_num_faces: int = 1, refine_landmarks: bool = True):
        self.refine_landmarks = refine_landmarks
        self.last_valid_landmarks: Optional[Dict[str, Any]] = None
        self.last_valid_time: float = 0.0
        self.consecutive_lost_frames: int = 0
        self.max_hold_frames: int = 2

        if HAS_MEDIAPIPE:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=max_num_faces,
                refine_landmarks=refine_landmarks,
                min_detection_confidence=0.25,
                min_tracking_confidence=0.25
            )
        else:
            self.face_mesh = None

        # Haar cascade classifiers for multi-tiered fallback
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )

        profile_path = cv2.data.haarcascades + 'haarcascade_profileface.xml'
        self.profile_cascade = cv2.CascadeClassifier(profile_path) if os.path.exists(profile_path) else None

    def process(self, frame_bgr: Optional[np.ndarray]) -> Dict[str, Any]:
        """
        Process BGR frame and return pixel coordinate landmarks and structured detection validity.
        Returns:
            Dict containing:
                - 'detection_validity': 'VALID', 'INVALID', or 'LOW_CONFIDENCE'
                - 'face_detected': bool
                - 'left_eye_valid': bool
                - 'right_eye_valid': bool
                - 'invalid_reason': Optional[str]
                - 'left_eye': Optional[np.ndarray] of shape (6, 2)
                - 'right_eye': Optional[np.ndarray] of shape (6, 2)
                - 'left_iris': Optional[np.ndarray] of shape (4, 2)
                - 'right_iris': Optional[np.ndarray] of shape (4, 2)
                - 'all_landmarks': Optional[np.ndarray] of shape (N, 2)
        """
        now = time.time()

        if frame_bgr is None or not hasattr(frame_bgr, "shape") or frame_bgr.size == 0 or len(frame_bgr.shape) != 3:
            return {
                "detection_validity": "INVALID",
                "face_detected": False,
                "left_eye_valid": False,
                "right_eye_valid": False,
                "invalid_reason": "INVALID_FRAME",
                "left_eye": None,
                "right_eye": None,
                "left_iris": None,
                "right_iris": None,
                "all_landmarks": None
            }

        h, w, _ = frame_bgr.shape
        if h < 20 or w < 20:
            return {
                "detection_validity": "INVALID",
                "face_detected": False,
                "left_eye_valid": False,
                "right_eye_valid": False,
                "invalid_reason": "FRAME_DIMENSIONS_TOO_SMALL",
                "left_eye": None,
                "right_eye": None,
                "left_iris": None,
                "right_iris": None,
                "all_landmarks": None
            }

        # 1. Primary: MediaPipe FaceMesh
        if HAS_MEDIAPIPE and self.face_mesh:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(frame_rgb)

            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]
                landmarks_np = np.array([
                    [lm.x * w, lm.y * h] for lm in face_landmarks.landmark
                ], dtype=np.float32)

                landmarks_3d_np = np.array([
                    [lm.x * w, lm.y * h, lm.z * w] for lm in face_landmarks.landmark
                ], dtype=np.float32)

                left_eye = landmarks_np[self.LEFT_EYE_INDICES]
                right_eye = landmarks_np[self.RIGHT_EYE_INDICES]
                left_eye_3d = landmarks_3d_np[self.LEFT_EYE_INDICES]
                right_eye_3d = landmarks_3d_np[self.RIGHT_EYE_INDICES]

                # Estimate 3D head pose (yaw, pitch, roll in degrees)
                head_pose = HeadPoseEstimator.estimate_pose(landmarks_np, img_shape=(h, w))
                yaw = head_pose.get("yaw", 0.0)

                # Compute face bounding box and scale
                fx_min = max(0, int(landmarks_np[:, 0].min()))
                fx_max = min(w, int(landmarks_np[:, 0].max()))
                fy_min = max(0, int(landmarks_np[:, 1].min()))
                fy_max = min(h, int(landmarks_np[:, 1].max()))
                face_box = (fx_min, fy_min, fx_max - fx_min, fy_max - fy_min)
                face_scale = float(fx_max - fx_min)

                # Validate eye landmarks explicitly
                l_valid, l_reason = EyeDetector.validate_eye_landmarks(left_eye, img_shape=(h, w))
                r_valid, r_reason = EyeDetector.validate_eye_landmarks(right_eye, img_shape=(h, w))

                # Independent eye visibility evaluation
                l_visibility = EyeDetector.evaluate_eye_visibility(
                    left_eye if l_valid else None,
                    img_shape=(h, w),
                    head_yaw=yaw,
                    is_left_eye=True
                )
                r_visibility = EyeDetector.evaluate_eye_visibility(
                    right_eye if r_valid else None,
                    img_shape=(h, w),
                    head_yaw=yaw,
                    is_left_eye=False
                )

                left_iris = None
                right_iris = None
                if len(landmarks_np) > 468:
                    left_iris = landmarks_np[self.LEFT_IRIS_INDICES]
                    right_iris = landmarks_np[self.RIGHT_IRIS_INDICES]

                # Determine overall detection validity:
                # When turning head, one eye may be occluded by nose, but the other remains cleanly visible!
                # Do not reject frame if one eye is cleanly visible and face is tracked.
                if l_valid and r_valid:
                    validity = "VALID"
                    invalid_reason = None
                elif l_valid and l_visibility in ("VISIBLE", "PARTIALLY_VISIBLE"):
                    validity = "VALID"
                    invalid_reason = None
                elif r_valid and r_visibility in ("VISIBLE", "PARTIALLY_VISIBLE"):
                    validity = "VALID"
                    invalid_reason = None
                elif l_valid or r_valid:
                    validity = "LOW_CONFIDENCE"
                    invalid_reason = f"PARTIAL_EYES_{l_reason or r_reason}"
                else:
                    validity = "INVALID"
                    invalid_reason = f"EYES_OUT_OF_BOUNDS_{l_reason}_{r_reason}"

                res = {
                    "detection_validity": validity,
                    "face_detected": True,
                    "face_box": face_box,
                    "face_scale": face_scale,
                    "head_pose": head_pose,
                    "left_eye_valid": l_valid,
                    "right_eye_valid": r_valid,
                    "left_eye_visibility": l_visibility,
                    "right_eye_visibility": r_visibility,
                    "tracking_status": "TRACKING",
                    "invalid_reason": invalid_reason,
                    "left_eye": left_eye if l_valid else None,
                    "right_eye": right_eye if r_valid else None,
                    "left_eye_3d": left_eye_3d if l_valid else None,
                    "right_eye_3d": right_eye_3d if r_valid else None,
                    "left_iris": left_iris,
                    "right_iris": right_iris,
                    "all_landmarks": landmarks_np
                }
                if validity == "VALID":
                    self.last_valid_landmarks = res
                    self.last_valid_time = now
                    self.consecutive_lost_frames = 0
                return res

        # 2. Short-term Tracking Continuity Bridge
        # If tracking flickered for 1-2 frames during rapid movement, hold last valid landmarks
        if self.last_valid_landmarks is not None and self.consecutive_lost_frames < self.max_hold_frames:
            if (now - self.last_valid_time) < 0.18:
                self.consecutive_lost_frames += 1
                res = dict(self.last_valid_landmarks)
                res["detection_validity"] = "LOW_CONFIDENCE"
                res["tracking_status"] = "REACQUIRING"
                res["invalid_reason"] = "TEMPORARY_TRACKING_DROPOUT"
                return res

        # 3. Secondary Fallback: OpenCV Cascades (Frontal + Profile)
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(60, 60))
        is_profile = False

        if len(faces) == 0 and self.profile_cascade is not None:
            # Try profile cascade for side/turned heads
            faces = self.profile_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=3, minSize=(60, 60))
            is_profile = True
            if len(faces) == 0:
                # Flip image to check other profile direction
                flipped = cv2.flip(gray, 1)
                flipped_faces = self.profile_cascade.detectMultiScale(flipped, scaleFactor=1.2, minNeighbors=3, minSize=(60, 60))
                if len(flipped_faces) > 0:
                    fx, fy, fw, fh = flipped_faces[0]
                    faces = [(w - fx - fw, fy, fw, fh)]
                    is_profile = True

        if len(faces) > 0:
            (fx, fy, fw, fh) = faces[0]
            roi_gray = gray[fy:fy + int(fh * 0.65), fx:fx + fw]
            eyes = self.eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.15, minNeighbors=3, minSize=(18, 18))

            if len(eyes) >= 1:
                sorted_eyes = sorted(eyes, key=lambda e: e[0])
                if len(sorted_eyes) >= 2:
                    r_ex, r_ey, r_ew, r_eh = sorted_eyes[0]
                    l_ex, l_ey, l_ew, l_eh = sorted_eyes[1]
                else:
                    r_ex, r_ey, r_ew, r_eh = sorted_eyes[0]
                    l_ex, l_ey, l_ew, l_eh = sorted_eyes[0]

                r_x = fx + r_ex
                r_y = fy + r_ey
                l_x = fx + l_ex
                l_y = fy + l_ey

                right_eye = np.array([
                    [r_x, r_y + r_eh * 0.5],
                    [r_x + r_ew * 0.28, r_y + r_eh * 0.2],
                    [r_x + r_ew * 0.72, r_y + r_eh * 0.2],
                    [r_x + r_ew, r_y + r_eh * 0.5],
                    [r_x + r_ew * 0.72, r_y + r_eh * 0.8],
                    [r_x + r_ew * 0.28, r_y + r_eh * 0.8],
                ], dtype=np.float32)

                left_eye = np.array([
                    [l_x, l_y + l_eh * 0.5],
                    [l_x + l_ew * 0.28, l_y + l_eh * 0.2],
                    [l_x + l_ew * 0.72, l_y + l_eh * 0.2],
                    [l_x + l_ew, l_y + l_eh * 0.5],
                    [l_x + l_ew * 0.72, l_y + l_eh * 0.8],
                    [l_x + l_ew * 0.28, l_y + l_eh * 0.8],
                ], dtype=np.float32)

                l_valid, l_reason = EyeDetector.validate_eye_landmarks(left_eye, img_shape=(h, w))
                r_valid, r_reason = EyeDetector.validate_eye_landmarks(right_eye, img_shape=(h, w))

                rcx, rcy = r_x + r_ew * 0.5, r_y + r_eh * 0.5
                lcx, lcy = l_x + l_ew * 0.5, l_y + l_eh * 0.5
                right_iris = np.array([[rcx - 2, rcy], [rcx, rcy - 2], [rcx + 2, rcy], [rcx, rcy + 2]], dtype=np.float32)
                left_iris = np.array([[lcx - 2, lcy], [lcx, lcy - 2], [lcx + 2, lcy], [lcx, lcy + 2]], dtype=np.float32)

                sim_yaw = 25.0 if is_profile else 0.0
                res = {
                    "detection_validity": "LOW_CONFIDENCE",
                    "face_detected": True,
                    "face_box": (fx, fy, fw, fh),
                    "face_scale": float(fw),
                    "head_pose": {"yaw": sim_yaw, "pitch": 0.0, "roll": 0.0},
                    "left_eye_valid": l_valid,
                    "right_eye_valid": r_valid,
                    "left_eye_visibility": "PARTIALLY_VISIBLE" if is_profile else "VISIBLE",
                    "right_eye_visibility": "OCCLUDED" if is_profile else "VISIBLE",
                    "tracking_status": "TRACKING",
                    "invalid_reason": "PROFILE_CASCADE_FALLBACK" if is_profile else "HAAR_CASCADE_FALLBACK",
                    "left_eye": left_eye if l_valid else None,
                    "right_eye": right_eye if r_valid else None,
                    "left_eye_3d": None,
                    "right_eye_3d": None,
                    "left_iris": left_iris,
                    "right_iris": right_iris,
                    "all_landmarks": np.vstack([left_eye, right_eye])
                }
                return res

        # 4. Detection failed completely: return explicit INVALID result
        self.last_valid_landmarks = None
        self.consecutive_lost_frames = 0
        return {
            "detection_validity": "INVALID",
            "face_detected": False,
            "face_box": None,
            "face_scale": None,
            "head_pose": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            "left_eye_valid": False,
            "right_eye_valid": False,
            "left_eye_visibility": "TRACKING_LOST",
            "right_eye_visibility": "TRACKING_LOST",
            "tracking_status": "LOST",
            "invalid_reason": "NO_FACE_DETECTED",
            "left_eye": None,
            "right_eye": None,
            "left_eye_3d": None,
            "right_eye_3d": None,
            "left_iris": None,
            "right_iris": None,
            "all_landmarks": None
        }

