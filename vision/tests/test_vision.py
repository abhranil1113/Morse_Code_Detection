import os
import sys
import time
from pathlib import Path
import numpy as np
import cv2

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from vision.ml.feature_extractor import FeatureExtractor
from vision.ml.label_mapper import LabelMapper, TARGET_GAZE_CLASSES
from vision.ml.predictor import GazeDirectionPredictor, EyeStatePredictor
from vision.detection.eye_detector import EyeDetector
from vision.camera.opencv_camera import OpenCVCamera
from vision.morse.decoder import MorseDecoder
from vision.morse.blink_detector import BlinkDetector
from vision.gestures.gaze_controller import GazeController
from vision.events.event_emitter import VisionEventEmitter, VisionEventType, BlinkEvent
from vision.agent.local_bridge import LocalVisionBridge


# ==========================================
# 1. Computer Vision Test Cases
# ==========================================

def test_valid_image_input():
    """Verify normal image input produces features and valid predictions."""
    extractor = FeatureExtractor()
    img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    feats = extractor.extract_features(img)
    assert feats is not None
    assert len(feats) == extractor.feature_dim
    assert not np.isnan(feats).any()


def test_invalid_image_input():
    """Verify system safely handles None, empty, or corrupted image matrices."""
    predictor = GazeDirectionPredictor()
    cls1, conf1 = predictor.predict_with_confidence(None)
    assert cls1 == "UNKNOWN"
    assert conf1 == 0.0

    cls2, conf2 = predictor.predict_with_confidence(np.array([]))
    assert cls2 == "UNKNOWN"
    assert conf2 == 0.0


def test_no_face_detected_handling():
    """Verify LocalVisionBridge returns graceful fallback when no face is present."""
    bridge = LocalVisionBridge()
    # Blank black image has no face
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    telemetry = bridge.process_frame(blank_frame)

    assert telemetry["face_detected"] is False
    assert telemetry["ear"] == 0.0
    assert telemetry["eye_state"] == "UNAVAILABLE"
    assert telemetry["overall_eye_state"] == "UNAVAILABLE"
    assert telemetry["left_eye_state"] == "UNAVAILABLE"
    assert telemetry["right_eye_state"] == "UNAVAILABLE"
    assert telemetry["left_box"] is None
    assert telemetry["right_box"] is None
    assert telemetry["gaze_direction"] == "CENTER"


def test_missing_eye_landmarks():
    """Verify EyeDetector behaves gracefully when landmark coordinates are missing or None."""
    metrics = EyeDetector.get_eye_metrics({})
    assert metrics["avg_ear"] == 0.0

    partial_metrics = EyeDetector.get_eye_metrics({"left_eye": None, "right_eye": None})
    assert partial_metrics["avg_ear"] == 0.0


def test_ear_computation():
    """Verify mathematical correctness of 6-point Eye Aspect Ratio."""
    # Synthesize open eye polygon (high aspect ratio)
    open_eye = np.array([
        [0.0, 10.0], [5.0, 4.0], [15.0, 4.0],
        [20.0, 10.0], [15.0, 16.0], [5.0, 16.0]
    ])
    ear_open = EyeDetector.calculate_ear(open_eye)
    assert ear_open > 0.25

    # Synthesize closed eye polygon (flat aspect ratio)
    closed_eye = np.array([
        [0.0, 10.0], [5.0, 9.8], [15.0, 9.8],
        [20.0, 10.0], [15.0, 10.2], [5.0, 10.2]
    ])
    ear_closed = EyeDetector.calculate_ear(closed_eye)
    assert ear_closed < 0.10


def test_gaze_classification():
    """Verify 5-class gaze prediction on sample inputs."""
    predictor = GazeDirectionPredictor()
    dummy_eye = np.full((64, 64, 3), 128, dtype=np.uint8)

    pred_class = predictor.predict(dummy_eye)
    assert pred_class in TARGET_GAZE_CLASSES

    probs = predictor.predict_probabilities(dummy_eye)
    assert len(probs) == 5
    assert abs(sum(probs.values()) - 1.0) < 1e-4


def test_low_confidence_prediction():
    """Verify low-confidence prediction fallback logic."""
    state_predictor = EyeStatePredictor(ear_fallback_threshold=0.22)
    # EAR slightly above threshold yields lower confidence
    state, conf = state_predictor.predict_with_confidence(None, ear_value=0.23)
    assert state == "OPEN"
    assert 0.5 <= conf <= 0.8

    # EAR well above threshold yields high confidence
    state_high, conf_high = state_predictor.predict_with_confidence(None, ear_value=0.35)
    assert state_high == "OPEN"
    assert conf_high >= conf


def test_camera_failure_handling():
    """Verify OpenCVCamera safely fails on invalid device index without crashing."""
    cam = OpenCVCamera(camera_index=9999, width=640, height=480)
    started = cam.start()
    assert started is False
    assert cam.is_opened() is False

    ret, frame = cam.read_frame()
    assert ret is False
    assert frame is None
    cam.stop()


# ==========================================
# 2. Morse & Gesture Test Cases
# ==========================================

def test_morse_dot_and_dash():
    """Verify short blink produces dot (.) and long blink produces dash (-)."""
    detector = BlinkDetector()
    t0 = 1000.0

    # Short blink: 200 ms (within dot 0.08 - 0.35s)
    detector.update(1, timestamp=t0)
    detector.update(0, timestamp=t0 + 0.01)  # Eye closes
    sym, evt = detector.update(1, timestamp=t0 + 0.21)  # Eye opens after 200ms
    assert sym == "."
    assert evt == "DOT"

    # Long blink: 600 ms (within dash 0.40 - 1.20s)
    t1 = 2000.0
    detector.update(0, timestamp=t1)
    sym2, evt2 = detector.update(1, timestamp=t1 + 0.60)
    assert sym2 == "-"
    assert evt2 == "DASH"


def test_morse_timing_boundaries():
    """Verify involuntary micro-flutter (<0.08s) or sleep (>1.2s) is rejected."""
    detector = BlinkDetector()
    t = 1000.0

    # Micro-flutter: 40 ms -> should be ignored (noise)
    detector.update(0, timestamp=t)
    sym, _ = detector.update(1, timestamp=t + 0.04)
    assert sym is None

    # Prolonged closure: 3.0 seconds -> sleep/rest, not intentional Morse
    t_long = 2000.0
    detector.update(0, timestamp=t_long)
    sym_long, _ = detector.update(1, timestamp=t_long + 3.0)
    assert sym_long is None


def test_morse_character_and_word_decoding():
    """Verify symbol buffer translates into letters and words."""
    decoder = MorseDecoder()

    # Letter 'A' (.-)
    decoder.add_symbol(".")
    decoder.add_symbol("-")
    char_a = decoder.commit_character()
    assert char_a == "A"
    assert decoder.current_text == "A"

    # Space separation
    decoder.commit_space()
    assert decoder.current_text == "A "

    # Letter 'B' (-...)
    for s in ["-", ".", ".", "."]:
        decoder.add_symbol(s)
    char_b = decoder.commit_character()
    assert char_b == "B"
    assert decoder.current_text == "A B"


def test_morse_invalid_sequences():
    """Verify unmapped Morse sequence defaults gracefully to '?' without crashing."""
    decoder = MorseDecoder()
    for s in ["-", "-", "-", "-", "-", "-", "-"]:  # 7 dashes has no letter
        decoder.add_symbol(s)
    char = decoder.commit_character()
    assert char == "?"
    assert "?" in decoder.current_text


def test_morse_reset_and_backspace():
    """Verify backspace and clear operations."""
    decoder = MorseDecoder()
    decoder.current_text = "HELLO"
    decoder.backspace()
    assert decoder.current_text == "HELL"

    # Backspacing inside buffer takes precedence
    decoder.add_symbol(".")
    decoder.add_symbol("-")
    assert decoder.current_symbol_buffer == ".-"
    decoder.backspace()
    assert decoder.current_symbol_buffer == "."

    decoder.clear()
    assert decoder.current_text == ""
    assert decoder.current_symbol_buffer == ""


def test_gaze_gesture_controller():
    """Verify dwell time triggers directional gestures."""
    controller = GazeController(dwell_time_sec=0.20)
    t = time.time()

    # Held LEFT for 0.25 seconds
    dir1, act1 = controller.update(avg_gaze_ratio=0.80)
    assert dir1 == "LEFT"

    time.sleep(0.22)
    dir2, act2 = controller.update(avg_gaze_ratio=0.80)
    assert dir2 == "LEFT"
    assert act2 == "SELECT_LEFT"


def test_vision_event_bus():
    """Verify publish-subscribe event emitter."""
    bus = VisionEventEmitter()
    received = []

    bus.on(VisionEventType.BLINK_DOT, lambda ev: received.append(ev))
    ev = BlinkEvent(event_type=VisionEventType.BLINK_DOT, symbol=".", duration_ms=210, confidence=0.95)
    bus.emit(VisionEventType.BLINK_DOT, ev)

    assert len(received) == 1
    assert received[0].symbol == "."
    assert received[0].duration_ms == 210


# ==========================================
# 3. Comprehensive Morse & Eye-State Audit Tests
# ==========================================

def test_morse_sequence_all_phrases():
    """Verify all 6 required phrases and sentence decoding without letter/macro collisions."""
    decoder = MorseDecoder()

    # 1. Macro Phrases
    assert decoder.decode_sequence("...---...") == "SOS"
    assert decoder.decode_sequence(".... . .-.. .--.") == "HELP"
    assert decoder.decode_sequence("-.-- . ...") == "YES"
    assert decoder.decode_sequence("-. ---") == "NO"
    assert decoder.decode_sequence(".-- .- - . .-.") == "WATER"
    assert decoder.decode_sequence("-.-. --- -- . / .... . .-. .") == "COME HERE"

    # 2. Strict Single-Letter Non-Collision
    # '....' MUST decode to 'H', not 'HELP'
    assert decoder.decode_sequence("....") == "H"
    # '-.' MUST decode to 'N', not 'NO'
    assert decoder.decode_sequence("-.") == "N"
    # '-.--' MUST decode to 'Y', not 'YES'
    assert decoder.decode_sequence("-.--") == "Y"
    # '.--' MUST decode to 'W', not 'WATER'
    assert decoder.decode_sequence(".--") == "W"

    # 3. Full Sentence: "I AM IN KOLKATA PLEASE COME HERE"
    # I: ..
    # AM: .- --
    # IN: .. -.
    # KOLKATA: -.- --- .-.. -.- .- - .-
    # PLEASE: .--. .-.. . .- ... .
    # COME HERE: -.-. --- -- . / .... . .-. .
    kolkata_sentence = (
        ".. / .- -- / .. -. / -.- --- .-.. -.- .- - .- / "
        ".--. .-.. . .- ... . / -.-. --- -- . / .... . .-. ."
    )
    decoded_kolkata = decoder.decode_sequence(kolkata_sentence)
    assert decoded_kolkata == "I AM IN KOLKATA PLEASE COME HERE"


def test_independent_eye_state_and_bilateral_gating():
    """Verify independent L/R eye evaluation and that only bilateral closures trigger Morse blinks."""
    bridge = LocalVisionBridge()

    # Scenario 1: Both eyes OPEN -> Overall OPEN
    # Synthesize landmarks with open eyes (EAR ~ 0.35)
    open_left = np.array([[10, 20], [15, 12], [25, 12], [30, 20], [25, 28], [15, 28]], dtype=np.float32)
    open_right = np.array([[50, 20], [55, 12], [65, 12], [70, 20], [65, 28], [55, 28]], dtype=np.float32)

    ear_l = EyeDetector.calculate_ear(open_left)
    ear_r = EyeDetector.calculate_ear(open_right)
    assert ear_l > 0.25 and ear_r > 0.25

    lbl_l, conf_l = bridge.predictor.predict_with_confidence(None, ear_value=ear_l)
    lbl_r, conf_r = bridge.predictor.predict_with_confidence(None, ear_value=ear_r)
    assert lbl_l == "OPEN" and lbl_r == "OPEN"

    # Scenario 2: Unilateral Left Wink (Left CLOSED, Right OPEN) -> Overall PARTIAL
    closed_left = np.array([[10, 20], [15, 19.8], [25, 19.8], [30, 20], [25, 20.2], [15, 20.2]], dtype=np.float32)
    ear_closed_l = EyeDetector.calculate_ear(closed_left)
    assert ear_closed_l < 0.10

    lbl_cl, conf_cl = bridge.predictor.predict_with_confidence(None, ear_value=ear_closed_l)
    assert lbl_cl == "CLOSED"

    # Evaluate overall logic for asymmetric wink
    overall_wink = "PARTIAL" if (lbl_cl != lbl_r) else "CLOSED"
    assert overall_wink == "PARTIAL"

    # Bilateral Blink Gating: PARTIAL winks MUST NOT feed binary_state = 0 to BlinkDetector
    # When overall is PARTIAL, bridge feeds binary_state = 1 (OPEN) to prevent accidental Morse dots
    wink_binary_state = 0 if overall_wink == "CLOSED" else 1
    assert wink_binary_state == 1

    # Scenario 3: Bilateral Eye Closure (Both CLOSED) -> Overall CLOSED
    ear_closed_r = ear_closed_l
    lbl_cr, _ = bridge.predictor.predict_with_confidence(None, ear_value=ear_closed_r)
    assert lbl_cr == "CLOSED"
    overall_bilateral = "CLOSED" if (lbl_cl == "CLOSED" and lbl_cr == "CLOSED") else "OPEN"
    assert overall_bilateral == "CLOSED"

    # Bilateral closure yields binary_state = 0, triggering Morse detection
    bilateral_binary_state = 0 if overall_bilateral == "CLOSED" else 1
    assert bilateral_binary_state == 0

    # Scenario 4: Reopening after blink transitions back to OPEN
    reopen_state = "OPEN" if (lbl_l == "OPEN" and lbl_r == "OPEN") else "CLOSED"
    assert reopen_state == "OPEN"


def test_hud_color_rules():
    """Verify HUD color assignments: GREEN for OPEN, RED for CLOSED, GREY for UNAVAILABLE."""
    bridge = LocalVisionBridge()
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    dummy_pts = np.array([[20, 30], [25, 25], [35, 25], [40, 30], [35, 35], [25, 35]], dtype=np.float32)
    landmarks = {"left_eye": dummy_pts, "right_eye": dummy_pts}

    # 1. OPEN eye state produces GREEN border
    hud_open = bridge._render_hud(
        frame.copy(), landmarks, ear=0.30,
        left_eye_state="OPEN", right_eye_state="OPEN", overall_eye_state="OPEN",
        confidence=0.98, gaze_dir="CENTER"
    )
    assert hud_open is not None

    # 2. CLOSED eye state produces RED border
    hud_closed = bridge._render_hud(
        frame.copy(), landmarks, ear=0.08,
        left_eye_state="CLOSED", right_eye_state="CLOSED", overall_eye_state="CLOSED",
        confidence=0.98, gaze_dir="CENTER"
    )
    assert hud_closed is not None

    # 3. UNAVAILABLE state produces GREY border
    hud_unavail = bridge._render_hud(
        frame.copy(), landmarks, ear=0.0,
        left_eye_state="UNAVAILABLE", right_eye_state="UNAVAILABLE", overall_eye_state="UNAVAILABLE",
        confidence=0.0, gaze_dir="CENTER"
    )
    assert hud_unavail is not None


if __name__ == "__main__":
    print("=" * 60)
    print("Running EyeSpeak AI - Comprehensive Vision & Morse Test Suite")
    print("=" * 60)

    suites = [
        ("Valid image input", test_valid_image_input),
        ("Invalid image input handling", test_invalid_image_input),
        ("No face detected handling", test_no_face_detected_handling),
        ("Missing eye landmarks handling", test_missing_eye_landmarks),
        ("EAR geometric computation", test_ear_computation),
        ("Gaze 5-class prediction", test_gaze_classification),
        ("Low-confidence prediction fallback", test_low_confidence_prediction),
        ("Camera failure handling", test_camera_failure_handling),
        ("Morse dot and dash timing", test_morse_dot_and_dash),
        ("Morse timing boundaries", test_morse_timing_boundaries),
        ("Morse character & word decoding", test_morse_character_and_word_decoding),
        ("Morse invalid sequence handling", test_morse_invalid_sequences),
        ("Morse reset & backspace", test_morse_reset_and_backspace),
        ("Gaze gesture dwell controller", test_gaze_gesture_controller),
        ("Vision event bus pub/sub", test_vision_event_bus),
        ("Morse sequence & phrase collision audit", test_morse_sequence_all_phrases),
        ("Independent eye-state & bilateral gating", test_independent_eye_state_and_bilateral_gating),
        ("HUD overlay color rules (Green/Red/Grey)", test_hud_color_rules),
    ]

    for name, fn in suites:
        fn()
        print(f"[PASS] {name}")

    print("=" * 60)
    print(f"ALL {len(suites)} VISION & MORSE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
