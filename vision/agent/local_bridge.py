import time
from typing import Dict, Any, Optional
import numpy as np
import cv2

from vision.detection.face_landmarker import FaceLandmarker
from vision.detection.eye_detector import EyeDetector
from vision.features.eye_cropper import EyeCropper
from vision.features.gaze_features import GazeFeatureExtractor
from vision.ml.predictor import EyeStatePredictor, GazeDirectionPredictor
from vision.morse.blink_detector import BlinkDetector
from vision.morse.decoder import MorseDecoder
from vision.gestures.gaze_controller import GazeController


class LocalVisionBridge:
    """Orchestrates real-time frame processing across vision, ML, and Morse modules."""

    def __init__(self):
        self.landmarker = FaceLandmarker()
        self.cropper = EyeCropper(target_size=(32, 32))
        self.predictor = EyeStatePredictor()
        try:
            self.gaze_predictor = GazeDirectionPredictor()
        except Exception:
            self.gaze_predictor = None
        self.blink_detector = BlinkDetector()
        self.morse_decoder = MorseDecoder()
        self.gaze_controller = GazeController()

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Processes a single BGR camera frame and returns a telemetry bundle.
        """
        now = time.time()
        landmarks_dict = self.landmarker.process(frame)

        if not landmarks_dict:
            return {
                "face_detected": False,
                "ear": 0.0,
                "left_ear": 0.0,
                "right_ear": 0.0,
                "left_eye_state": "UNAVAILABLE",
                "right_eye_state": "UNAVAILABLE",
                "overall_eye_state": "UNAVAILABLE",
                "eye_state": "UNAVAILABLE",
                "left_eye_confidence": 0.0,
                "right_eye_confidence": 0.0,
                "eye_detection_confidence": 0.0,
                "confidence": 0.0,
                "current_buffer": self.morse_decoder.current_symbol_buffer,
                "decoded_text": self.morse_decoder.current_text,
                "gaze_direction": "CENTER",
                "gesture_action": None,
                "left_box": None,
                "right_box": None,
                "timestamp": now,
                "processed_frame": frame
            }

        # 1. Calculate Eye Aspect Ratio (EAR) for both eyes
        metrics = EyeDetector.get_eye_metrics(landmarks_dict)
        left_ear = metrics["left_ear"]
        right_ear = metrics["right_ear"]
        avg_ear = metrics["avg_ear"]

        # 2. Crop both eyes & predict state independently via Machine Learning
        left_eye_pts = landmarks_dict.get("left_eye")
        right_eye_pts = landmarks_dict.get("right_eye")
        left_crop = self.cropper.crop_eye(frame, left_eye_pts)
        right_crop = self.cropper.crop_eye(frame, right_eye_pts)

        left_label, left_conf = self.predictor.predict_with_confidence(left_crop, ear_value=left_ear)
        right_label, right_conf = self.predictor.predict_with_confidence(right_crop, ear_value=right_ear)

        # Enforce confidence thresholds
        left_eye_state = left_label if left_conf >= 0.50 else "UNAVAILABLE"
        right_eye_state = right_label if right_conf >= 0.50 else "UNAVAILABLE"

        # Determine overall eye state
        if left_eye_state == "CLOSED" and right_eye_state == "CLOSED":
            overall_eye_state = "CLOSED"
            binary_state = 0  # Bilateral blink for Morse
        elif left_eye_state == "OPEN" and right_eye_state == "OPEN":
            overall_eye_state = "OPEN"
            binary_state = 1
        elif left_eye_state == "UNAVAILABLE" and right_eye_state == "UNAVAILABLE":
            overall_eye_state = "UNAVAILABLE"
            binary_state = 1
        else:
            # Asymmetric closure (wink): preserve independent state, do not trigger accidental Morse blink
            overall_eye_state = "PARTIAL"
            binary_state = 1

        avg_confidence = round((left_conf + right_conf) / 2.0, 2)

        # 3. Blink State Machine & Morse Decoding (Bilateral closures only)
        sym, event = self.blink_detector.update(binary_state, timestamp=now)
        if sym:
            self.morse_decoder.add_symbol(sym)

        if event == "CHAR_COMPLETE":
            self.morse_decoder.commit_character()
        elif event == "WORD_COMPLETE":
            self.morse_decoder.commit_space()

        # 4. Gaze Direction via trained ML model and iris ratio fallback
        predicted_gaze = None
        if self.gaze_predictor is not None and left_crop is not None and left_crop.size > 0:
            try:
                predicted_gaze = self.gaze_predictor.predict(left_crop)
            except Exception:
                pass

        left_ratio = GazeFeatureExtractor.get_gaze_ratio(
            landmarks_dict.get("left_eye"),
            landmarks_dict.get("left_iris")
        )
        right_ratio = GazeFeatureExtractor.get_gaze_ratio(
            landmarks_dict.get("right_eye"),
            landmarks_dict.get("right_iris")
        )
        avg_gaze = (left_ratio + right_ratio) / 2.0
        gaze_dir, gesture_action = self.gaze_controller.update(
            avg_gaze_ratio=avg_gaze,
            predicted_gaze=predicted_gaze
        )

        # 5. Standardized Gaze Gestures:
        # UP    -> SEND_MESSAGE
        # DOWN  -> BACKSPACE
        # RIGHT -> SPACE (Dedicated intentional gesture)
        # LEFT  -> CLEAR_BUFFER (Cancel uncommitted dots/dashes)
        if gesture_action == "SELECT_DOWN":
            self.morse_decoder.backspace()
        elif gesture_action == "SELECT_RIGHT":
            self.morse_decoder.commit_space()
        elif gesture_action == "SELECT_LEFT":
            self.morse_decoder.clear_symbol_buffer()
        elif gesture_action == "SELECT_UP":
            # Gaze UP initiates confirm/send action
            gesture_action = "SEND_MESSAGE"

        # 6. Extract dynamic eye bounding boxes for frontend tracking
        h, w = frame.shape[:2]
        left_box = None
        if left_eye_pts is not None and len(left_eye_pts) > 0:
            lx_min, ly_min, lx_max, ly_max = EyeDetector.get_eye_bounding_box(left_eye_pts, padding=8, img_shape=(h, w))
            left_box = {
                "x": round(lx_min / w, 4),
                "y": round(ly_min / h, 4),
                "width": round((lx_max - lx_min) / w, 4),
                "height": round((ly_max - ly_min) / h, 4)
            }

        right_box = None
        if right_eye_pts is not None and len(right_eye_pts) > 0:
            rx_min, ry_min, rx_max, ry_max = EyeDetector.get_eye_bounding_box(right_eye_pts, padding=8, img_shape=(h, w))
            right_box = {
                "x": round(rx_min / w, 4),
                "y": round(ry_min / h, 4),
                "width": round((rx_max - rx_min) / w, 4),
                "height": round((ry_max - ry_min) / h, 4)
            }

        # 7. Render HUD Overlay on Frame
        annotated_frame = self._render_hud(
            frame.copy(),
            landmarks_dict,
            avg_ear,
            left_eye_state,
            right_eye_state,
            overall_eye_state,
            avg_confidence,
            gaze_dir,
            gesture_action
        )

        return {
            "face_detected": True,
            "ear": round(avg_ear, 3),
            "left_ear": round(left_ear, 3),
            "right_ear": round(right_ear, 3),
            "left_eye_state": left_eye_state,
            "right_eye_state": right_eye_state,
            "overall_eye_state": overall_eye_state,
            "eye_state": overall_eye_state,
            "left_eye_confidence": round(left_conf, 2),
            "right_eye_confidence": round(right_conf, 2),
            "eye_detection_confidence": avg_confidence,
            "confidence": avg_confidence,
            "current_buffer": self.morse_decoder.current_symbol_buffer,
            "decoded_text": self.morse_decoder.current_text,
            "gaze_direction": gaze_dir,
            "gesture_action": gesture_action,
            "left_box": left_box,
            "right_box": right_box,
            "timestamp": now,
            "processed_frame": annotated_frame
        }

    def _render_hud(
        self,
        frame: np.ndarray,
        landmarks: Dict[str, np.ndarray],
        ear: float,
        left_eye_state: str,
        right_eye_state: str,
        overall_eye_state: str,
        confidence: float,
        gaze_dir: str,
        gesture_action: Optional[str] = None
    ) -> np.ndarray:
        h, w = frame.shape[:2]

        eye_configs = [
            ("left_eye", "L-EYE", left_eye_state),
            ("right_eye", "R-EYE", right_eye_state)
        ]

        # 1. Draw Eye Bounding Focus Squares (GREEN for OPEN, RED for CLOSED, GREY for UNAVAILABLE)
        for key, label, st in eye_configs:
            pts = landmarks.get(key)
            if pts is not None and len(pts) > 0:
                x_min, y_min, x_max, y_max = EyeDetector.get_eye_bounding_box(pts, padding=8, img_shape=(h, w))
                if st == "OPEN":
                    box_color = (0, 255, 0)      # Green
                elif st == "CLOSED":
                    box_color = (0, 0, 255)      # Red
                else:
                    box_color = (128, 128, 128)  # Grey

                # Primary rectangle around eye
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), box_color, 2)

                # Focus target corners
                c_len = max(4, min(10, (x_max - x_min) // 3))
                cv2.line(frame, (x_min, y_min), (x_min + c_len, y_min), box_color, 2)
                cv2.line(frame, (x_min, y_min), (x_min, y_min + c_len), box_color, 2)
                cv2.line(frame, (x_max, y_min), (x_max - c_len, y_min), box_color, 2)
                cv2.line(frame, (x_max, y_min), (x_max, y_min + c_len), box_color, 2)
                cv2.line(frame, (x_min, y_max), (x_min + c_len, y_max), box_color, 2)
                cv2.line(frame, (x_min, y_max), (x_min, y_max - c_len), box_color, 2)
                cv2.line(frame, (x_max, y_max), (x_max - c_len, y_max), box_color, 2)
                cv2.line(frame, (x_max, y_max), (x_max, y_max - c_len), box_color, 2)

                tag = f"{label} [{st}]"
                cv2.putText(frame, tag, (x_min, max(18, y_min - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, box_color, 1)

        # 2. Draw eye contours
        for key in ["left_eye", "right_eye"]:
            pts = landmarks.get(key)
            if pts is not None:
                cv2.polylines(frame, [pts.astype(np.int32)], True, (0, 255, 255), 1)

        # 3. Draw irises
        for key in ["left_iris", "right_iris"]:
            pts = landmarks.get(key)
            if pts is not None:
                for pt in pts:
                    cv2.circle(frame, (int(pt[0]), int(pt[1])), 2, (0, 255, 0), -1)

        # HUD Top Banner
        cv2.rectangle(frame, (0, 0), (w, 55), (20, 20, 20), -1)

        if overall_eye_state == "OPEN":
            status_text = "EYES OPEN"
            banner_color = (0, 255, 0)
        elif overall_eye_state == "CLOSED":
            status_text = "BLINK DETECTED"
            banner_color = (0, 0, 255)
        elif overall_eye_state == "PARTIAL":
            status_text = "PARTIAL BLINK"
            banner_color = (0, 165, 255)
        else:
            status_text = "EYES NOT DETECTED"
            banner_color = (128, 128, 128)

        cv2.putText(frame, f"STATUS: {status_text} ({int(confidence*100)}%)", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, banner_color, 2)
        cv2.putText(frame, f"EAR: {ear:.2f}", (310, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"GAZE: {gaze_dir}", (430, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
        if gesture_action:
            cv2.putText(frame, f"ACT: {gesture_action}", (540, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)

        # HUD Bottom Text Bar
        cv2.rectangle(frame, (0, h - 60), (w, h), (15, 15, 15), -1)
        buf_str = self.morse_decoder.current_symbol_buffer or "_"
        cv2.putText(frame, f"BUFFER: {buf_str}", (15, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"TEXT: {self.morse_decoder.current_text}", (15, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame
