"""
EyeSpeak AI - Webcam Blink Sequence Collector
Collects structured time-series sequences of natural blinks, intentional Morse blinks,
open eyes, closed eyes, and invalid-detection frames for temporal validation and offline analysis.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List
import cv2
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from vision.camera.opencv_camera import OpenCVCamera
from vision.agent.local_bridge import LocalVisionBridge
from vision.detection.eye_detector import EyeDetector


LABEL_MENU = {
    "1": "natural_blink",
    "2": "intentional_short_blink",
    "3": "intentional_long_blink",
    "4": "eyes_open",
    "5": "eyes_closed",
    "6": "invalid_detection"
}


def collect_blink_sequences(
    output_dir: str = "database/datasets/raw/webcam_blinks",
    camera_index: int = 0
):
    print("=" * 70)
    print("EyeSpeak AI - Temporal Blink Sequence Data Collector")
    print("Captures real-time time-series streams of timestamps, EAR, validity, and eye states.")
    print("=" * 70)
    print("Available Sequence Labels:")
    for key, label in LABEL_MENU.items():
        print(f"  [{key}] {label}")
    print("  [r] Start/Stop Recording Active Sequence")
    print("  [q] Quit Collector")
    print("=" * 70)

    save_dir = Path(output_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    cam = OpenCVCamera(camera_index=camera_index, width=640, height=480)
    if not cam.start():
        print(f"[Error] Could not initialize camera at index {camera_index}.")
        return

    bridge = LocalVisionBridge()

    active_label = "natural_blink"
    is_recording = False
    recorded_frames: List[Dict[str, Any]] = []
    session_start_time = 0.0

    try:
        while True:
            ret, frame = cam.read_frame()
            if not ret or frame is None:
                continue

            now = time.time()
            telemetry = bridge.process_frame(frame)
            annotated_frame = telemetry.get("processed_frame", frame).copy()

            if is_recording:
                elapsed = now - session_start_time
                entry = {
                    "timestamp": round(now, 4),
                    "elapsed_sec": round(elapsed, 4),
                    "intended_label": active_label,
                    "detection_validity": telemetry.get("detection_validity", "INVALID"),
                    "invalid_reason": telemetry.get("invalid_reason"),
                    "face_detected": telemetry.get("face_detected", False),
                    "left_ear": telemetry.get("left_ear"),
                    "right_ear": telemetry.get("right_ear"),
                    "avg_ear": telemetry.get("ear"),
                    "left_eye_state": telemetry.get("left_eye_state", "UNKNOWN"),
                    "right_eye_state": telemetry.get("right_eye_state", "UNKNOWN"),
                    "overall_eye_state": telemetry.get("overall_eye_state", "UNKNOWN"),
                    "confidence": telemetry.get("confidence", 0.0),
                    "morse_buffer": telemetry.get("current_buffer", ""),
                    "decoded_text": telemetry.get("decoded_text", "")
                }
                recorded_frames.append(entry)

                # Recording HUD indicator
                cv2.circle(annotated_frame, (w := annotated_frame.shape[1] - 30, 30), 10, (0, 0, 255), -1)
                cv2.putText(
                    annotated_frame,
                    f"REC: {active_label} ({len(recorded_frames)} frames)",
                    (w - 280, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    2
                )
            else:
                cv2.putText(
                    annotated_frame,
                    f"TARGET LABEL: {active_label} (Press 'r' to record)",
                    (20, annotated_frame.shape[0] - 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 255),
                    2
                )

            cv2.imshow("EyeSpeak Sequence Collector", annotated_frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif chr(key) in LABEL_MENU:
                active_label = LABEL_MENU[chr(key)]
                print(f"[Selected Target Label]: {active_label}")
            elif key == ord('r'):
                if not is_recording:
                    # Start recording
                    is_recording = True
                    recorded_frames = []
                    session_start_time = now
                    print(f"\n[RECORDING STARTED] Label: {active_label}")
                else:
                    # Stop recording and persist sequence
                    is_recording = False
                    duration = now - session_start_time
                    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                    seq_filename = f"{active_label}_{timestamp_str}.json"
                    seq_path = save_dir / seq_filename

                    seq_data = {
                        "metadata": {
                            "label": active_label,
                            "recorded_at": timestamp_str,
                            "duration_sec": round(duration, 3),
                            "total_frames": len(recorded_frames),
                            "fps": round(len(recorded_frames) / duration, 2) if duration > 0 else 0.0
                        },
                        "frames": recorded_frames
                    }

                    with open(seq_path, "w") as f:
                        json.dump(seq_data, f, indent=2)

                    print(f"[RECORDING SAVED] {seq_path} ({len(recorded_frames)} frames in {duration:.2f}s)\n")

    finally:
        cam.stop()
        cv2.destroyAllWindows()
        print("Sequence collector closed.")


if __name__ == "__main__":
    collect_blink_sequences()
