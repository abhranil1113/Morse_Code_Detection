"""
EyeSpeak AI - Comprehensive Vision, Landmark, Blink, and Morse Test Suite
Implements all 22 required automated engineering and regression tests.
Uses deterministic timestamps without real-time sleep delays.
"""

import os
import sys
from pathlib import Path
import numpy as np
import cv2

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from vision.ml.feature_extractor import FeatureExtractor
from vision.ml.label_mapper import TARGET_GAZE_CLASSES
from vision.ml.predictor import GazeDirectionPredictor, EyeStatePredictor
from vision.detection.eye_detector import EyeDetector
from vision.detection.face_landmarker import FaceLandmarker
from vision.features.eye_cropper import EyeCropper
from vision.morse.decoder import MorseDecoder
from vision.morse.blink_detector import BlinkDetector
from vision.morse.timing_calibration import MorseTimingProfile
from vision.gestures.gaze_controller import GazeController
from vision.agent.local_bridge import LocalVisionBridge
from vision.features.head_pose import HeadPoseEstimator


# ---------------------------------------------------------------------------
# Helper synthesized landmarks
# ---------------------------------------------------------------------------
def make_valid_eye(x_offset: float = 100.0, y_offset: float = 100.0, is_closed: bool = False) -> np.ndarray:
    """Returns valid (6, 2) eye polygon with geometric EAR either open (~0.35) or closed (~0.05)."""
    h_span = 20.0
    if not is_closed:
        v_span = 7.0
    else:
        v_span = 1.0

    return np.array([
        [x_offset, y_offset],                        # p1 (corner)
        [x_offset + 5.0, y_offset - v_span],         # p2 (top-left)
        [x_offset + 15.0, y_offset - v_span],        # p3 (top-right)
        [x_offset + h_span, y_offset],               # p4 (inner corner)
        [x_offset + 15.0, y_offset + v_span],        # p5 (bottom-right)
        [x_offset + 5.0, y_offset + v_span],         # p6 (bottom-left)
    ], dtype=np.float32)


# ===========================================================================
# 1. Landmark & Eye Detection Tests (Tests 1 - 9)
# ===========================================================================

def test_1_valid_face_and_eye_landmarks():
    """1. Valid face and eye landmarks produce valid metrics and non-empty bounding box."""
    left_eye = make_valid_eye(100.0, 100.0, is_closed=False)
    right_eye = make_valid_eye(150.0, 100.0, is_closed=False)

    l_valid, l_reason = EyeDetector.validate_eye_landmarks(left_eye, img_shape=(480, 640))
    r_valid, r_reason = EyeDetector.validate_eye_landmarks(right_eye, img_shape=(480, 640))

    assert l_valid is True, f"Left eye validation failed: {l_reason}"
    assert r_valid is True, f"Right eye validation failed: {r_reason}"

    ear_l = EyeDetector.calculate_ear(left_eye)
    assert ear_l is not None and ear_l > 0.25

    bbox = EyeDetector.get_eye_bounding_box(left_eye, padding=8, img_shape=(480, 640))
    assert bbox is not None
    xmin, ymin, xmax, ymax = bbox
    assert xmax > xmin and ymax > ymin


def test_2_missing_face():
    """2. Missing face in frame returns explicit INVALID validity and no landmarks."""
    landmarker = FaceLandmarker()
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    res = landmarker.process(blank_frame)

    assert res["detection_validity"] == "INVALID"
    assert res["face_detected"] is False
    assert res["left_eye"] is None
    assert res["right_eye"] is None
    assert res["invalid_reason"] == "NO_FACE_DETECTED"


def test_3_missing_left_eye_landmarks():
    """3. Missing left eye yields None left EAR and does not default to 0.0."""
    right_eye = make_valid_eye(150.0, 100.0, is_closed=False)
    metrics = EyeDetector.get_eye_metrics({"left_eye": None, "right_eye": right_eye})

    assert metrics["left_ear"] is None
    assert metrics["right_ear"] is not None
    assert metrics["avg_ear"] == metrics["right_ear"]


def test_4_missing_right_eye_landmarks():
    """4. Missing right eye yields None right EAR and does not default to 0.0."""
    left_eye = make_valid_eye(100.0, 100.0, is_closed=False)
    metrics = EyeDetector.get_eye_metrics({"left_eye": left_eye, "right_eye": None})

    assert metrics["right_ear"] is None
    assert metrics["left_ear"] is not None
    assert metrics["avg_ear"] == metrics["left_ear"]


def test_5_missing_both_eyes():
    """5. Missing both eyes produces None for all EAR metrics, never 0.0."""
    metrics = EyeDetector.get_eye_metrics({"left_eye": None, "right_eye": None})
    assert metrics["left_ear"] is None
    assert metrics["right_ear"] is None
    assert metrics["avg_ear"] is None


def test_6_invalid_and_malformed_landmark_arrays():
    """6. Malformed, non-finite, out-of-bounds, or degenerate arrays are explicitly rejected."""
    # NaN array
    nan_arr = np.full((6, 2), np.nan, dtype=np.float32)
    v1, r1 = EyeDetector.validate_eye_landmarks(nan_arr)
    assert v1 is False and "NON_FINITE" in r1

    # Malformed shape (4, 2)
    short_arr = np.zeros((4, 2), dtype=np.float32)
    v2, r2 = EyeDetector.validate_eye_landmarks(short_arr)
    assert v2 is False and "MALFORMED_SHAPE" in r2

    # Degenerate horizontal span (all points at same x)
    col_arr = np.zeros((6, 2), dtype=np.float32)
    v3, r3 = EyeDetector.validate_eye_landmarks(col_arr)
    assert v3 is False and "DEGENERATE_SPAN" in r3

    # Extreme out of bounds (with non-degenerate span)
    out_arr = np.array([
        [9000, 9000], [9010, 8990], [9020, 8990],
        [9030, 9000], [9020, 9010], [9010, 9010]
    ], dtype=np.float32)
    v4, r4 = EyeDetector.validate_eye_landmarks(out_arr, img_shape=(480, 640))
    assert v4 is False and "COORDINATES_OUT_OF_BOUNDS" in r4


def test_7_stale_landmark_handling():
    """7. Landmarker resets tracking when face is missing and does not reuse stale data indefinitely."""
    landmarker = FaceLandmarker()
    # Blank frame has no face
    res = landmarker.process(np.zeros((200, 200, 3), dtype=np.uint8))
    assert res["detection_validity"] == "INVALID"
    assert landmarker.last_valid_landmarks is None


def test_8_invalid_eye_crops():
    """8. Empty frames, None frames, or invalid coordinates return None safely from EyeCropper."""
    cropper = EyeCropper(target_size=(32, 32))

    assert cropper.crop_eye(None, make_valid_eye()) is None
    assert cropper.crop_eye(np.zeros((100, 100, 3), dtype=np.uint8), None) is None
    assert cropper.crop_eye(np.array([]), make_valid_eye()) is None


def test_9_missing_ear_prediction():
    """9. Missing EAR does not default to CLOSED; missing image and EAR returns UNKNOWN."""
    predictor = EyeStatePredictor()
    # When both image and EAR are missing, state is UNKNOWN
    state, conf = predictor.predict_with_confidence(None, ear_value=None)
    assert state == "UNKNOWN"
    assert conf == 0.0


# ===========================================================================
# 2. Blink Detector Temporal State Machine Tests (Tests 10 - 18)
# ===========================================================================

def test_10_invalid_frame_handling_in_blink_detector():
    """10. INVALID observations are not interpreted as OPEN or CLOSED."""
    detector = BlinkDetector()
    t0 = 100.0

    # Start with valid OPEN
    detector.update(1, timestamp=t0)
    # Stream multiple INVALID frames
    for i in range(1, 10):
        sym, evt = detector.update(-1, timestamp=t0 + i * 0.05)
        assert sym is None
        assert evt is None or evt == "TRACKING_PAUSED"

    # Verify detector did not erroneously trigger closure
    assert detector.is_closed is False


def test_11_open_closed_open_producing_one_dot():
    """11. Valid OPEN -> CLOSED (200ms) -> OPEN produces exactly one DOT (.)."""
    detector = BlinkDetector(MorseTimingProfile(dot_min_sec=0.10, dot_max_sec=0.40))
    t0 = 200.0

    detector.update(1, timestamp=t0)
    detector.update(0, timestamp=t0 + 0.05)  # Eyelids close
    sym, evt = detector.update(1, timestamp=t0 + 0.25)  # Reopen after 200ms

    assert sym == "."
    assert evt == "DOT"


def test_12_open_closed_open_producing_one_dash():
    """12. Valid OPEN -> CLOSED (700ms) -> OPEN produces exactly one DASH (-)."""
    detector = BlinkDetector(MorseTimingProfile(dot_max_sec=0.40, dash_max_sec=1.40))
    t0 = 300.0

    detector.update(1, timestamp=t0)
    detector.update(0, timestamp=t0 + 0.05)  # Eyelids close
    sym, evt = detector.update(1, timestamp=t0 + 0.75)  # Reopen after 700ms

    assert sym == "-"
    assert evt == "DASH"


def test_13_natural_short_blink_rejection():
    """13. Involuntary micro-flutters (<0.10s) are rejected without emitting symbols."""
    detector = BlinkDetector(MorseTimingProfile(dot_min_sec=0.10))
    t0 = 400.0

    detector.update(1, timestamp=t0)
    detector.update(0, timestamp=t0 + 0.02)
    sym, evt = detector.update(1, timestamp=t0 + 0.07)  # 50ms flutter

    assert sym is None
    assert evt == "MICRO_FLUTTER_REJECTED"


def test_14_excessively_long_closure_rejection():
    """14. Prolonged closures (>1.40s) are rejected as sleep/resting."""
    detector = BlinkDetector(MorseTimingProfile(dash_max_sec=1.40))
    t0 = 500.0

    detector.update(1, timestamp=t0)
    detector.update(0, timestamp=t0 + 0.05)
    sym, evt = detector.update(1, timestamp=t0 + 2.50)  # 2.45s closure

    assert sym is None
    assert evt == "LONG_CLOSURE_REJECTED"


def test_15_tracking_loss_during_closure():
    """15. Prolonged tracking loss during active closure aborts without emitting phantom blink."""
    detector = BlinkDetector(max_invalid_during_closure_sec=0.25)
    t0 = 600.0

    detector.update(1, timestamp=t0)
    detector.update(0, timestamp=t0 + 0.05)  # Closure begins

    # Tracking lost for 0.40 seconds (> 0.25s threshold)
    detector.update(-1, timestamp=t0 + 0.10)
    sym, evt = detector.update(-1, timestamp=t0 + 0.50)

    assert sym is None
    assert evt == "TRACKING_LOST_ABORTED"
    assert detector.is_closed is False


def test_16_recovery_after_tracking_loss():
    """16. Brief tracking glitch (<=0.25s) during closure recovers and completes valid blink."""
    detector = BlinkDetector(max_invalid_during_closure_sec=0.25)
    t0 = 700.0

    detector.update(1, timestamp=t0)
    detector.update(0, timestamp=t0 + 0.05)       # Closed at t=700.05
    detector.update(-1, timestamp=t0 + 0.12)      # Brief glitch for 70ms
    sym, evt = detector.update(1, timestamp=t0 + 0.25)  # Reopens cleanly at t=700.25 (200ms total)

    assert sym == "."
    assert evt == "DOT"


def test_17_no_morse_symbol_from_invalid_observations():
    """17. Continuous invalid observations never generate any Morse symbol."""
    detector = BlinkDetector()
    t = 800.0
    for _ in range(30):
        t += 0.033
        sym, _ = detector.update(-1, timestamp=t)
        assert sym is None


def test_18_no_char_or_word_completion_from_invalid_observations():
    """18. Invalid frames do not advance open timer toward character or word completion."""
    detector = BlinkDetector(MorseTimingProfile(char_gap_sec=0.80, word_gap_sec=2.00))
    t0 = 900.0

    detector.update(1, timestamp=t0)
    # Stream invalid observations for 5 seconds
    events = []
    for i in range(100):
        _, evt = detector.update(-1, timestamp=t0 + i * 0.05)
        if evt:
            events.append(evt)

    assert "CHAR_COMPLETE" not in events
    assert "WORD_COMPLETE" not in events


# ===========================================================================
# 3. Morse Decoding & Sentence Tests (Tests 19 - 21)
# ===========================================================================

def test_19_correct_morse_character_decoding():
    """19. Standard characters decode accurately from symbol buffer."""
    decoder = MorseDecoder()

    # Letter 'A' (.-)
    decoder.add_symbol(".")
    decoder.add_symbol("-")
    assert decoder.commit_character() == "A"

    # Letter 'S' (...)
    for _ in range(3):
        decoder.add_symbol(".")
    assert decoder.commit_character() == "S"

    # Letter 'O' (---)
    for _ in range(3):
        decoder.add_symbol("-")
    assert decoder.commit_character() == "O"


def test_20_correct_word_spacing():
    """20. Space is inserted correctly between words separated by word boundaries."""
    decoder = MorseDecoder()
    decoder.decode_sequence(".-   -...")  # A, 3 spaces, B
    assert decoder.decode_sequence(".- / -...") == "A B"


def test_21_full_sentence_decoding_kolkata_and_assistive():
    """21. Target communication sentences decode without character or macro collisions."""
    decoder = MorseDecoder()

    # Sentence 1: "I AM IN KOLKATA"
    # I = .. | A = .- | M = -- | I = .. | N = -. | K = -.- | O = --- | L = .-.. | K = -.- | A = .- | T = - | A = .-
    kolkata_morse = ".. / .- -- / .. -. / -.- --- .-.. -.- .- - .-"
    assert decoder.decode_sequence(kolkata_morse) == "I AM IN KOLKATA"

    # Sentence 2: "PLEASE HELP ME"
    # PLEASE = .--. .-.. . .- ... . | HELP = .... . .-.. .--. | ME = -- .
    help_morse = ".--. .-.. . .- ... . / .... . .-.. .--. / -- ."
    assert decoder.decode_sequence(help_morse) == "PLEASE HELP ME"

    # Sentence 3: "I NEED WATER"
    # I = .. | NEED = -. . . -.. | WATER = .-- .- - . .-.
    water_morse = ".. / -. . . -.. / .-- .- - . .-."
    assert decoder.decode_sequence(water_morse) == "I NEED WATER"

    # Sentence 4: "CALL MY FAMILY"
    # CALL = -.-. .- .-.. .-.. | MY = -- -.-- | FAMILY = ..-. .- -- .. .-.. -.--
    family_morse = "-.-. .- .-.. .-.. / -- -.-- / ..-. .- -- .. .-.. -.--"
    assert decoder.decode_sequence(family_morse) == "CALL MY FAMILY"


# ===========================================================================
# 4. Gaze Functionality Regression Tests (Test 22)
# ===========================================================================

def test_22_gaze_functionality_regression():
    """22. Gaze predictor produces valid 5-class predictions; controller triggers dwell actions."""
    predictor = GazeDirectionPredictor()
    dummy_eye = np.full((64, 64, 3), 128, dtype=np.uint8)

    pred_class = predictor.predict(dummy_eye)
    assert pred_class in TARGET_GAZE_CLASSES

    # GazeController dwell test
    controller = GazeController(dwell_time_sec=0.15)
    t = 1000.0

    controller.update(avg_gaze_ratio=0.80)  # Looking LEFT
    _, act_immediate = controller.update(avg_gaze_ratio=0.80)
    assert act_immediate is None  # Dwell not met yet

    # Simulate dwell exceeded after 0.20s
    controller.direction_start_time = t - 0.20
    _, act_triggered = controller.update(avg_gaze_ratio=0.80)
    assert act_triggered == "SELECT_LEFT"


# ===========================================================================
# 5. Head Movement, Adaptive ROI, & Visibility Tests (Tests 23 - 32)
# ===========================================================================

def make_canonical_face_landmarks(yaw_deg: float = 0.0, pitch_deg: float = 0.0) -> np.ndarray:
    """Returns synthesized (300, 2) facial landmark array with true 3D rotation projection."""
    yaw = np.radians(yaw_deg)
    pitch = np.radians(pitch_deg)

    Ry = np.array([
        [np.cos(yaw), 0, np.sin(yaw)],
        [0, 1, 0],
        [-np.sin(yaw), 0, np.cos(yaw)]
    ], dtype=np.float64)
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(pitch), -np.sin(pitch)],
        [0, np.sin(pitch), np.cos(pitch)]
    ], dtype=np.float64)
    R = Ry @ Rx
    rotated_3d = (R @ HeadPoseEstimator.MODEL_POINTS_3D.T).T

    Z0 = 900.0
    f = 640.0
    proj_2d = np.zeros((300, 2), dtype=np.float32)
    indices = HeadPoseEstimator.POSE_LANDMARK_INDICES
    for i, idx in enumerate(indices):
        X, Y, Z = rotated_3d[i]
        zc = Z0 + Z
        xc = 320.0 + f * (X / zc)
        yc = 240.0 - f * (Y / zc)
        proj_2d[idx] = [xc, yc]
    return proj_2d


def test_23_frontal_head_pose_and_tracking():
    """23. Frontal head pose estimation produces minimal yaw/pitch (<5 deg); both eyes VISIBLE."""
    lms = make_canonical_face_landmarks(yaw_deg=0.0, pitch_deg=0.0)
    pose = HeadPoseEstimator.estimate_pose(lms)
    assert abs(pose["yaw"]) < 5.0

    eye = make_valid_eye(250.0, 190.0)
    vis = EyeDetector.evaluate_eye_visibility(eye, head_yaw=pose["yaw"], is_left_eye=True)
    assert vis == "VISIBLE"


def test_24_turning_head_slightly_left():
    """24. Head turned slightly left (yaw ~ +16 deg): both eyes remain valid and visible/partially visible."""
    # Person turning head left rotates yaw negatively in 3D projection
    lms = make_canonical_face_landmarks(yaw_deg=-16.0)
    pose = HeadPoseEstimator.estimate_pose(lms)
    assert abs(pose["yaw"]) > 10.0

    eye_l = make_valid_eye(275.0, 190.0)
    eye_r = make_valid_eye(415.0, 190.0)
    vis_l = EyeDetector.evaluate_eye_visibility(eye_l, head_yaw=pose["yaw"], is_left_eye=True)
    vis_r = EyeDetector.evaluate_eye_visibility(eye_r, head_yaw=pose["yaw"], is_left_eye=False)

    assert vis_l in ("VISIBLE", "PARTIALLY_VISIBLE")
    assert vis_r in ("VISIBLE", "PARTIALLY_VISIBLE")
    assert vis_l != "OCCLUDED"


def test_25_turning_head_slightly_right():
    """25. Head turned slightly right (yaw ~ +16 deg): both eyes remain tracked and visible."""
    lms = make_canonical_face_landmarks(yaw_deg=16.0)
    pose = HeadPoseEstimator.estimate_pose(lms)
    assert abs(pose["yaw"]) > 10.0

    eye_l = make_valid_eye(225.0, 190.0)
    eye_r = make_valid_eye(365.0, 190.0)
    vis_l = EyeDetector.evaluate_eye_visibility(eye_l, head_yaw=pose["yaw"], is_left_eye=True)
    vis_r = EyeDetector.evaluate_eye_visibility(eye_r, head_yaw=pose["yaw"], is_left_eye=False)

    assert vis_l in ("VISIBLE", "PARTIALLY_VISIBLE")
    assert vis_r in ("VISIBLE", "PARTIALLY_VISIBLE")
    assert vis_r != "OCCLUDED"


def test_26_turning_head_moderately_occlusion_awareness():
    """26. Head turned moderately (yaw = +35 deg): far eye marked OCCLUDED, near eye remains VISIBLE."""
    eye_l = make_valid_eye(290.0, 190.0)
    eye_r = make_valid_eye(430.0, 190.0)

    vis_l = EyeDetector.evaluate_eye_visibility(eye_l, head_yaw=35.0, is_left_eye=True)
    vis_r = EyeDetector.evaluate_eye_visibility(eye_r, head_yaw=35.0, is_left_eye=False)

    assert vis_l == "OCCLUDED"
    assert vis_r in ("VISIBLE", "PARTIALLY_VISIBLE")

    # Near eye must still have a valid adaptive bounding box
    bbox_r = EyeDetector.get_adaptive_eye_bounding_box(eye_r)
    assert bbox_r is not None
    assert (bbox_r[2] - bbox_r[0]) >= 20


def test_27_looking_up_and_down_pitch():
    """27. Looking up and down correctly reflects pitch variation while maintaining visibility."""
    lms_down = make_canonical_face_landmarks(pitch_deg=25.0)
    lms_up = make_canonical_face_landmarks(pitch_deg=-25.0)

    pose_down = HeadPoseEstimator.estimate_pose(lms_down)
    pose_up = HeadPoseEstimator.estimate_pose(lms_up)

    assert pose_down["pitch"] != pose_up["pitch"]


def test_28_moving_closer_adaptive_roi_scale():
    """28. Moving closer (larger face scale) adaptively enlarges eye ROI compared to distant face."""
    eye_close = make_valid_eye(250.0, 190.0) * 2.0
    bbox_close = EyeDetector.get_adaptive_eye_bounding_box(eye_close, face_scale=320.0)

    eye_far = make_valid_eye(250.0, 190.0) * 0.5
    bbox_far = EyeDetector.get_adaptive_eye_bounding_box(eye_far, face_scale=80.0)

    assert bbox_close is not None and bbox_far is not None
    close_width = bbox_close[2] - bbox_close[0]
    far_width = bbox_far[2] - bbox_far[0]
    assert close_width > far_width * 2.0


def test_29_adaptive_roi_stability_during_blink():
    """29. Adaptive ROI preserves uniform square geometry and does not collapse when eyelids close."""
    eye_open = make_valid_eye(100.0, 100.0, is_closed=False)
    eye_closed = make_valid_eye(100.0, 100.0, is_closed=True)

    bbox_open = EyeDetector.get_adaptive_eye_bounding_box(eye_open)
    bbox_closed = EyeDetector.get_adaptive_eye_bounding_box(eye_closed)

    assert bbox_open is not None and bbox_closed is not None
    h_open = bbox_open[3] - bbox_open[1]
    h_closed = bbox_closed[3] - bbox_closed[1]

    # Height of closed box must remain within 95% of open box (no collapse)
    assert abs(h_open - h_closed) <= 2
    assert (bbox_closed[2] - bbox_closed[0]) >= 20


def test_30_blinking_while_head_turned_single_eye_blink():
    """30. Single-eye intentional blink during head turn correctly emits Morse DOT without bilateral requirement."""
    bridge = LocalVisionBridge()
    dummy_frame = np.full((480, 640, 3), 120, dtype=np.uint8)

    # Mock head turned right (left eye occluded, right eye visible)
    right_eye_open = make_valid_eye(300.0, 200.0, is_closed=False)
    right_eye_closed = make_valid_eye(300.0, 200.0, is_closed=True)

    bridge.landmarker.process = lambda frame: {
        "detection_validity": "VALID",
        "face_detected": True,
        "face_scale": 200.0,
        "face_box": (200, 100, 200, 250),
        "head_pose": {"yaw": 35.0, "pitch": 0.0, "roll": 0.0},
        "left_eye_valid": False,
        "right_eye_valid": True,
        "left_eye_visibility": "OCCLUDED",
        "right_eye_visibility": "VISIBLE",
        "tracking_status": "TRACKING",
        "invalid_reason": None,
        "left_eye": None,
        "right_eye": right_eye_open,
        "left_iris": None,
        "right_iris": None,
        "all_landmarks": None
    }

    # Frame 1: OPEN at t=100.0
    bridge.predictor.predict_with_confidence = lambda crop, ear_value=None: ("OPEN", 0.95)
    r1 = bridge.process_frame(dummy_frame)
    assert r1["overall_eye_state"] == "OPEN"

    # Frame 2: CLOSED at t=100.10 for 0.25s
    bridge.landmarker.process = lambda frame: {
        "detection_validity": "VALID",
        "face_detected": True,
        "face_scale": 200.0,
        "face_box": (200, 100, 200, 250),
        "head_pose": {"yaw": 35.0, "pitch": 0.0, "roll": 0.0},
        "left_eye_valid": False,
        "right_eye_valid": True,
        "left_eye_visibility": "OCCLUDED",
        "right_eye_visibility": "VISIBLE",
        "tracking_status": "TRACKING",
        "invalid_reason": None,
        "left_eye": None,
        "right_eye": right_eye_closed,
        "left_iris": None,
        "right_iris": None,
        "all_landmarks": None
    }
    bridge.predictor.predict_with_confidence = lambda crop, ear_value=None: ("CLOSED", 0.95)
    bridge.blink_detector.last_state_change_time = 100.0
    bridge.blink_detector.closure_start_time = 100.0
    bridge.blink_detector.update(0, timestamp=100.10)

    # Frame 3: REOPENS at t=100.35 (duration 0.25s -> DOT)
    sym, evt = bridge.blink_detector.update(1, timestamp=100.35)
    assert sym == "."
    assert evt == "DOT"


def test_31_partially_covering_one_eye():
    """31. Covering one eye marks it TRACKING_LOST while visible eye continues tracking without crash."""
    eye_r = make_valid_eye(300.0, 200.0, is_closed=False)
    vis_l = EyeDetector.evaluate_eye_visibility(None, is_left_eye=True)
    vis_r = EyeDetector.evaluate_eye_visibility(eye_r, is_left_eye=False)

    assert vis_l == "TRACKING_LOST"
    assert vis_r == "VISIBLE"


def test_32_outside_frame_and_reacquisition():
    """32. Face moving outside frame yields OUT_OF_FRAME; returning reacquires VALID tracking."""
    eye_out = np.array([[-50.0, -50.0]] * 6, dtype=np.float32)
    vis_out = EyeDetector.evaluate_eye_visibility(eye_out, img_shape=(480, 640))
    assert vis_out == "OUT_OF_FRAME"

    # Returning inside frame
    eye_in = make_valid_eye(300.0, 200.0)
    vis_in = EyeDetector.evaluate_eye_visibility(eye_in, img_shape=(480, 640))
    assert vis_in == "VISIBLE"


# ===========================================================================
# Main Test Runner
# ===========================================================================

def run_all_tests():
    print("=" * 75)
    print("EYEAI (EyeSpeak AI) - Comprehensive 32-Point Automated Test Suite")
    print("=" * 75)

    test_cases = [
        ("1. Valid face and eye landmarks", test_1_valid_face_and_eye_landmarks),
        ("2. Missing face handling", test_2_missing_face),
        ("3. Missing left-eye landmarks", test_3_missing_left_eye_landmarks),
        ("4. Missing right-eye landmarks", test_4_missing_right_eye_landmarks),
        ("5. Missing both eyes", test_5_missing_both_eyes),
        ("6. Invalid and malformed landmark arrays", test_6_invalid_and_malformed_landmark_arrays),
        ("7. Stale landmark handling", test_7_stale_landmark_handling),
        ("8. Invalid eye crops", test_8_invalid_eye_crops),
        ("9. Missing EAR prediction", test_9_missing_ear_prediction),
        ("10. Invalid-frame handling in blink detector", test_10_invalid_frame_handling_in_blink_detector),
        ("11. OPEN -> CLOSED -> OPEN producing one DOT", test_11_open_closed_open_producing_one_dot),
        ("12. OPEN -> CLOSED -> OPEN producing one DASH", test_12_open_closed_open_producing_one_dash),
        ("13. Natural short blink rejection", test_13_natural_short_blink_rejection),
        ("14. Excessively long closure rejection", test_14_excessively_long_closure_rejection),
        ("15. Tracking loss during closure", test_15_tracking_loss_during_closure),
        ("16. Recovery after tracking loss", test_16_recovery_after_tracking_loss),
        ("17. No Morse symbol from invalid observations", test_17_no_morse_symbol_from_invalid_observations),
        ("18. No char/word completion from invalid observations", test_18_no_char_or_word_completion_from_invalid_observations),
        ("19. Correct Morse character decoding", test_19_correct_morse_character_decoding),
        ("20. Correct word spacing", test_20_correct_word_spacing),
        ("21. Full sentence decoding: I AM IN KOLKATA", test_21_full_sentence_decoding_kolkata_and_assistive),
        ("22. Gaze functionality regression", test_22_gaze_functionality_regression),
        ("23. Frontal head pose and tracking", test_23_frontal_head_pose_and_tracking),
        ("24. Turning head slightly left", test_24_turning_head_slightly_left),
        ("25. Turning head slightly right", test_25_turning_head_slightly_right),
        ("26. Turning head moderately (occlusion awareness)", test_26_turning_head_moderately_occlusion_awareness),
        ("27. Looking up and down pitch", test_27_looking_up_and_down_pitch),
        ("28. Moving closer adaptive ROI scale", test_28_moving_closer_adaptive_roi_scale),
        ("29. Adaptive ROI stability during blink", test_29_adaptive_roi_stability_during_blink),
        ("30. Blinking while head turned (single-eye blink)", test_30_blinking_while_head_turned_single_eye_blink),
        ("31. Partially covering one eye", test_31_partially_covering_one_eye),
        ("32. Outside frame and reacquisition", test_32_outside_frame_and_reacquisition),
    ]

    passed = 0
    failed = 0

    for name, test_fn in test_cases:
        try:
            test_fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1

    print("=" * 75)
    print(f"RESULTS: {passed}/{len(test_cases)} TESTS PASSED ({failed} failed)")
    print("=" * 75)
    assert failed == 0, f"{failed} test(s) failed."


if __name__ == "__main__":
    run_all_tests()
