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
        Processes a single BGR camera frame and returns a structured telemetry bundle.
        Enforces strict invalid-frame isolation: missing landmarks never produce Morse symbols.
        """
        now = time.time()
        landmarks_dict = self.landmarker.process(frame)

        validity = landmarks_dict.get("detection_validity", "INVALID")
        invalid_reason = landmarks_dict.get("invalid_reason")

        # -------------------------------------------------------------
        # 1. Invalid Frame Handling
        # -------------------------------------------------------------
        if validity == "INVALID" or not landmarks_dict.get("face_detected", False):
            # Pass explicit INVALID observation to state machine so any active closure is handled safely
            sym, event = self.blink_detector.update(-1, timestamp=now)
            if sym:
                self.morse_decoder.add_symbol(sym)
            if event == "CHAR_COMPLETE":
                self.morse_decoder.commit_character()
            elif event == "WORD_COMPLETE":
                self.morse_decoder.commit_space()

            return {
                "face_detected": False,
                "detection_validity": "INVALID",
                "invalid_reason": invalid_reason or "NO_FACE_DETECTED",
                "left_eye_valid": False,
                "right_eye_valid": False,
                "ear": None,
                "left_ear": None,
                "right_ear": None,
                "left_eye_state": "UNKNOWN",
                "right_eye_state": "UNKNOWN",
                "overall_eye_state": "UNKNOWN",
                "eye_state": "UNKNOWN",
                "left_eye_confidence": 0.0,
                "right_eye_confidence": 0.0,
                "eye_detection_confidence": 0.0,
                "confidence": 0.0,
                "current_closure_duration": self.blink_detector.get_current_closure_duration(now),
                "current_buffer": self.morse_decoder.current_symbol_buffer,
                "decoded_text": self.morse_decoder.current_text,
                "gaze_direction": "CENTER",
                "gesture_action": None,
                "left_box": None,
                "right_box": None,
                "timestamp": now,
                "processed_frame": frame
            }

        # -------------------------------------------------------------
        # 2. Valid / Low-Confidence Frame Processing
        # -------------------------------------------------------------
        h, w = frame.shape[:2]

        face_scale = landmarks_dict.get("face_scale")
        face_box = landmarks_dict.get("face_box")
        head_pose = landmarks_dict.get("head_pose", {"yaw": 0.0, "pitch": 0.0, "roll": 0.0})
        left_eye_visibility = landmarks_dict.get("left_eye_visibility", "VISIBLE")
        right_eye_visibility = landmarks_dict.get("right_eye_visibility", "VISIBLE")
        tracking_status = landmarks_dict.get("tracking_status", "TRACKING")

        # Calculate Eye Aspect Ratio (EAR) for both eyes
        metrics = EyeDetector.get_eye_metrics(landmarks_dict, img_shape=(h, w))
        left_ear = metrics["left_ear"]
        right_ear = metrics["right_ear"]
        avg_ear = metrics["avg_ear"]

        # Crop both eyes using adaptive scale & predict state via Machine Learning
        left_eye_pts = landmarks_dict.get("left_eye")
        right_eye_pts = landmarks_dict.get("right_eye")
        left_crop = self.cropper.crop_eye(frame, left_eye_pts, face_scale=face_scale)
        right_crop = self.cropper.crop_eye(frame, right_eye_pts, face_scale=face_scale)

        left_label, left_conf = self.predictor.predict_with_confidence(left_crop, ear_value=left_ear)
        right_label, right_conf = self.predictor.predict_with_confidence(right_crop, ear_value=right_ear)

        # Enforce confidence thresholds
        left_eye_state = left_label if left_conf >= 0.50 else "UNKNOWN"
        right_eye_state = right_label if right_conf >= 0.50 else "UNKNOWN"

        # Determine overall eye state taking head movement and visibility into account
        l_is_usable = left_eye_visibility in ("VISIBLE", "PARTIALLY_VISIBLE") and left_eye_state != "UNKNOWN"
        r_is_usable = right_eye_visibility in ("VISIBLE", "PARTIALLY_VISIBLE") and right_eye_state != "UNKNOWN"

        if l_is_usable and r_is_usable:
            # Both eyes visible: bilateral evaluation
            if left_eye_state == "CLOSED" and right_eye_state == "CLOSED":
                overall_eye_state = "CLOSED"
                obs_state = 0
            elif (left_eye_state == "CLOSED" or right_eye_state == "CLOSED") and avg_ear is not None and avg_ear < 0.19:
                overall_eye_state = "CLOSED"
                obs_state = 0
            elif left_eye_state == "OPEN" and right_eye_state == "OPEN":
                overall_eye_state = "OPEN"
                obs_state = 1
            else:
                overall_eye_state = "PARTIAL"
                obs_state = 1
        elif l_is_usable and not r_is_usable:
            # User rotated head rightwards: left eye is cleanly visible, right is occluded or turned
            overall_eye_state = left_eye_state
            obs_state = 0 if left_eye_state == "CLOSED" else (1 if left_eye_state == "OPEN" else -1)
        elif r_is_usable and not l_is_usable:
            # User rotated head leftwards: right eye is cleanly visible, left is occluded or turned
            overall_eye_state = right_eye_state
            obs_state = 0 if right_eye_state == "CLOSED" else (1 if right_eye_state == "OPEN" else -1)
        else:
            # Neither eye is cleanly visible / both occluded or out of frame
            overall_eye_state = "UNKNOWN"
            obs_state = -1

        avg_confidence = round((left_conf + right_conf) / 2.0, 2)

        # -------------------------------------------------------------
        # 3. Blink State Machine & Morse Decoding
        # -------------------------------------------------------------
        sym, event = self.blink_detector.update(obs_state, timestamp=now)
        if sym:
            self.morse_decoder.add_symbol(sym)

        if event == "CHAR_COMPLETE":
            self.morse_decoder.commit_character()
        elif event == "WORD_COMPLETE":
            self.morse_decoder.commit_space()

        # -------------------------------------------------------------
        # 4. Gaze Direction (only on valid frames)
        # -------------------------------------------------------------
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

        # Standardized Gaze Gestures:
        if gesture_action == "SELECT_DOWN":
            self.morse_decoder.backspace()
        elif gesture_action == "SELECT_RIGHT":
            self.morse_decoder.commit_space()
        elif gesture_action == "SELECT_LEFT":
            self.morse_decoder.clear_symbol_buffer()
        elif gesture_action == "SELECT_UP":
            gesture_action = "SEND_MESSAGE"

        # -------------------------------------------------------------
        # 5. Extract Adaptive Eye and Face Bounding Boxes for UI Overlay
        # -------------------------------------------------------------
        left_box = None
        if left_eye_pts is not None and len(left_eye_pts) > 0:
            bbox_l = EyeDetector.get_adaptive_eye_bounding_box(left_eye_pts, face_scale=face_scale, img_shape=(h, w))
            if bbox_l is not None:
                lx_min, ly_min, lx_max, ly_max = bbox_l
                left_box = {
                    "x": round(lx_min / w, 4),
                    "y": round(ly_min / h, 4),
                    "width": round((lx_max - lx_min) / w, 4),
                    "height": round((ly_max - ly_min) / h, 4)
                }

        right_box = None
        if right_eye_pts is not None and len(right_eye_pts) > 0:
            bbox_r = EyeDetector.get_adaptive_eye_bounding_box(right_eye_pts, face_scale=face_scale, img_shape=(h, w))
            if bbox_r is not None:
                rx_min, ry_min, rx_max, ry_max = bbox_r
                right_box = {
                    "x": round(rx_min / w, 4),
                    "y": round(ry_min / h, 4),
                    "width": round((rx_max - rx_min) / w, 4),
                    "height": round((ry_max - ry_min) / h, 4)
                }

        face_box_norm = None
        if face_box is not None:
            fx, fy, fw_b, fh_b = face_box
            face_box_norm = {
                "x": round(fx / w, 4),
                "y": round(fy / h, 4),
                "width": round(fw_b / w, 4),
                "height": round(fh_b / h, 4)
            }

        # -------------------------------------------------------------
        # 6. Render Enriched HUD Overlay
        # -------------------------------------------------------------
        annotated_frame = self._render_hud(
            frame.copy(),
            landmarks_dict,
            avg_ear,
            left_eye_state,
            right_eye_state,
            overall_eye_state,
            avg_confidence,
            validity,
            gaze_dir,
            gesture_action,
            head_pose=head_pose,
            left_eye_visibility=left_eye_visibility,
            right_eye_visibility=right_eye_visibility,
            tracking_status=tracking_status
        )

        return {
            "face_detected": True,
            "detection_validity": validity,
            "invalid_reason": invalid_reason,
            "face_box": face_box_norm,
            "head_pose": head_pose,
            "head_yaw": head_pose.get("yaw", 0.0),
            "head_pitch": head_pose.get("pitch", 0.0),
            "tracking_status": tracking_status,
            "left_eye_valid": landmarks_dict.get("left_eye_valid", True),
            "right_eye_valid": landmarks_dict.get("right_eye_valid", True),
            "left_eye_visibility": left_eye_visibility,
            "right_eye_visibility": right_eye_visibility,
            "ear": round(avg_ear, 3) if avg_ear is not None else None,
            "left_ear": round(left_ear, 3) if left_ear is not None else None,
            "right_ear": round(right_ear, 3) if right_ear is not None else None,
            "left_eye_state": left_eye_state,
            "right_eye_state": right_eye_state,
            "overall_eye_state": overall_eye_state,
            "eye_state": overall_eye_state,
            "left_eye_confidence": round(left_conf, 2),
            "right_eye_confidence": round(right_conf, 2),
            "eye_detection_confidence": avg_confidence,
            "confidence": avg_confidence,
            "current_closure_duration": self.blink_detector.get_current_closure_duration(now),
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
        landmarks: Dict[str, Any],
        ear: Optional[float],
        left_eye_state: str,
        right_eye_state: str,
        overall_eye_state: str,
        confidence: float,
        validity: str,
        gaze_dir: str,
        gesture_action: Optional[str] = None,
        head_pose: Optional[Dict[str, float]] = None,
        left_eye_visibility: str = "VISIBLE",
        right_eye_visibility: str = "VISIBLE",
        tracking_status: str = "TRACKING"
    ) -> np.ndarray:
        h, w = frame.shape[:2]
        face_scale = landmarks.get("face_scale")
        yaw = head_pose.get("yaw", 0.0) if head_pose else 0.0
        pitch = head_pose.get("pitch", 0.0) if head_pose else 0.0

        # 1. Draw Face Bounding Box with Orientation Indicator
        face_box = landmarks.get("face_box")
        if face_box is not None:
            fx, fy, fw, fh = face_box
            cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (255, 180, 0), 1)
            cv2.putText(
                frame,
                f"FACE [Y:{yaw:+.0f} P:{pitch:+.0f}]",
                (fx, max(18, fy - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.40,
                (255, 180, 0),
                1
            )

        eye_configs = [
            ("left_eye", "L-EYE", left_eye_state, left_eye_visibility),
            ("right_eye", "R-EYE", right_eye_state, right_eye_visibility)
        ]

        # 2. Draw Adaptive Eye Bounding Focus Squares
        for key, label, st, vis in eye_configs:
            pts = landmarks.get(key)
            if pts is not None and len(pts) > 0:
                bbox = EyeDetector.get_adaptive_eye_bounding_box(
                    pts,
                    face_scale=face_scale,
                    img_shape=(h, w)
                )
                if bbox is not None:
                    x_min, y_min, x_max, y_max = bbox
                    if st == "OPEN" and vis == "VISIBLE":
                        box_color = (0, 255, 0)      # Green
                    elif st == "CLOSED":
                        box_color = (0, 0, 255)      # Red
                    elif vis == "OCCLUDED":
                        box_color = (0, 140, 255)    # Orange
                    elif vis == "PARTIALLY_VISIBLE" or validity == "LOW_CONFIDENCE":
                        box_color = (0, 215, 255)    # Yellow
                    else:
                        box_color = (128, 128, 128)  # Grey

                    # Primary adaptive rectangle around eye
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
                    cv2.line(frame, (x_max, y_max), (x_max - c_len, y_max), box_color, 2)

                    tag = f"{label} [{st} | {vis[:5]}]"
                    cv2.putText(frame, tag, (x_min, max(18, y_min - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, box_color, 1)

        # 3. Draw eye contours
        for key in ["left_eye", "right_eye"]:
            pts = landmarks.get(key)
            if pts is not None:
                cv2.polylines(frame, [pts.astype(np.int32)], True, (0, 255, 255), 1)

        # 4. Draw irises
        for key in ["left_iris", "right_iris"]:
            pts = landmarks.get(key)
            if pts is not None:
                for pt in pts:
                    cv2.circle(frame, (int(pt[0]), int(pt[1])), 2, (0, 255, 0), -1)

        # 5. Top HUD Banner (Two-tiered for rich telemetry)
        cv2.rectangle(frame, (0, 0), (w, 58), (20, 20, 20), -1)

        if validity == "INVALID":
            status_text = "EYES NOT DETECTED"
            banner_color = (128, 128, 128)
        elif overall_eye_state == "OPEN":
            status_text = "EYES OPEN"
            banner_color = (0, 255, 0)
        elif overall_eye_state == "CLOSED":
            status_text = "BLINK DETECTED"
            banner_color = (0, 0, 255)
        elif overall_eye_state == "PARTIAL" or validity == "LOW_CONFIDENCE":
            status_text = "PARTIAL / LOW CONF"
            banner_color = (0, 215, 255)
        else:
            status_text = "EYES UNKNOWN"
            banner_color = (128, 128, 128)

        ear_str = f"{ear:.2f}" if ear is not None else "N/A"
        trk_color = (0, 255, 128) if tracking_status == "TRACKING" else (0, 165, 255)

        # Banner Row 1: Status, EAR, Head Pose, Tracking
        cv2.putText(frame, f"STATUS: {status_text} ({int(confidence*100)}%)", (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, banner_color, 2)
        cv2.putText(frame, f"EAR: {ear_str}", (280, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2)
        cv2.putText(frame, f"HEAD: Y={yaw:+.0f} P={pitch:+.0f}", (380, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 220, 255), 2)
        cv2.putText(frame, f"TRK: {tracking_status}", (540, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, trk_color, 2)

        # Banner Row 2: Visibility, Gaze, Action
        cv2.putText(frame, f"VIS: L={left_eye_visibility[:6]} R={right_eye_visibility[:6]}", (12, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)
        cv2.putText(frame, f"GAZE: {gaze_dir}", (280, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1)
        if gesture_action:
            cv2.putText(frame, f"ACT: {gesture_action}", (430, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)

        # HUD Bottom Text Bar
        cv2.rectangle(frame, (0, h - 60), (w, h), (15, 15, 15), -1)
        buf_str = self.morse_decoder.current_symbol_buffer or "_"
        cv2.putText(frame, f"BUFFER: {buf_str}", (15, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"TEXT: {self.morse_decoder.current_text}", (15, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame
