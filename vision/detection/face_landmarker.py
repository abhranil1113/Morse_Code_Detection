from typing import Optional, List, Tuple, Dict
import numpy as np
import cv2

try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False


class FaceLandmarker:
    """Detects facial landmarks using MediaPipe FaceMesh or Haar Cascade fallback."""

    # Key landmark indices for Eye Aspect Ratio (EAR) & Iris
    LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
    LEFT_IRIS_INDICES = [468, 469, 470, 471]
    RIGHT_IRIS_INDICES = [473, 474, 475, 476]

    def __init__(self, max_num_faces: int = 1, refine_landmarks: bool = True):
        self.refine_landmarks = refine_landmarks
        if HAS_MEDIAPIPE:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=max_num_faces,
                refine_landmarks=refine_landmarks,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.face_mesh = None
            # Haar cascade fallback
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )

    def process(self, frame_bgr: np.ndarray) -> Optional[Dict[str, np.ndarray]]:
        """
        Process BGR frame and return pixel coordinate landmarks for left and right eyes.
        Returns:
            Dict containing:
                - 'left_eye': np.ndarray of shape (6, 2)
                - 'right_eye': np.ndarray of shape (6, 2)
                - 'left_iris': np.ndarray of shape (4, 2) if available
                - 'right_iris': np.ndarray of shape (4, 2) if available
                - 'all_landmarks': (N, 2) array
        """
        h, w, _ = frame_bgr.shape

        if HAS_MEDIAPIPE and self.face_mesh:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(frame_rgb)

            if not results.multi_face_landmarks:
                return None

            face_landmarks = results.multi_face_landmarks[0]
            landmarks_np = np.array([
                [lm.x * w, lm.y * h] for lm in face_landmarks.landmark
            ], dtype=np.float32)

            left_eye = landmarks_np[self.LEFT_EYE_INDICES]
            right_eye = landmarks_np[self.RIGHT_EYE_INDICES]

            left_iris = None
            right_iris = None
            if len(landmarks_np) > 468:
                left_iris = landmarks_np[self.LEFT_IRIS_INDICES]
                right_iris = landmarks_np[self.RIGHT_IRIS_INDICES]

            return {
                "left_eye": left_eye,
                "right_eye": right_eye,
                "left_iris": left_iris,
                "right_iris": right_iris,
                "all_landmarks": landmarks_np
            }

        # Haar cascade fallback logic
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) == 0:
            return None

        (fx, fy, fw, fh) = faces[0]
        roi_gray = gray[fy:fy + fh, fx:fx + fw]
        eyes = self.eye_cascade.detectMultiScale(roi_gray)
        if len(eyes) < 2:
            return None

        return {
            "face_box": (fx, fy, fw, fh),
            "eyes_detected": len(eyes)
        }
