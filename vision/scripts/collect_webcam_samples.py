import os
import sys
from pathlib import Path
import cv2

# Add root to sys path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from vision.camera.opencv_camera import OpenCVCamera
from vision.detection.face_landmarker import FaceLandmarker
from vision.features.eye_cropper import EyeCropper


def collect_samples():
    print("=" * 60)
    print("EyeSpeak AI - Personal Webcam Sample Collector")
    print("Instructions:")
    print(" - Press 'c' to capture a CLOSED eye sample")
    print(" - Press 'o' to capture an OPEN eye sample")
    print(" - Press 'q' to finish and exit")
    print("=" * 60)

    base_dir = Path("database/datasets/raw/webcam_samples")
    closed_dir = base_dir / "closed"
    open_dir = base_dir / "open"
    closed_dir.mkdir(parents=True, exist_ok=True)
    open_dir.mkdir(parents=True, exist_ok=True)

    cam = OpenCVCamera(camera_index=0)
    if not cam.start():
        print("Error: Could not access camera.")
        return

    landmarker = FaceLandmarker()
    cropper = EyeCropper(target_size=(32, 32))

    closed_count = len(list(closed_dir.glob("*.png")))
    open_count = len(list(open_dir.glob("*.png")))

    try:
        while True:
            ret, frame = cam.read_frame()
            if not ret or frame is None:
                continue

            landmarks = landmarker.process(frame)
            display = frame.copy()

            if landmarks:
                left_eye = landmarks.get("left_eye")
                crop = cropper.crop_eye(frame, left_eye)
                if crop is not None:
                    # Draw thumbnail in top right
                    crop_bgr = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
                    crop_large = cv2.resize(crop_bgr, (96, 96))
                    display[10:106, -106:-10] = crop_large

            # On-screen text
            cv2.putText(display, f"Open: {open_count} (Press 'o')", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display, f"Closed: {closed_count} (Press 'c')", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display, "Press 'q' to quit", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            cv2.imshow("Webcam Calibration Collector", display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('o') and landmarks:
                crop = cropper.crop_eye(frame, landmarks.get("left_eye"))
                if crop is not None:
                    open_count += 1
                    cv2.imwrite(str(open_dir / f"open_{open_count:04d}.png"), crop)
                    print(f"Captured Open sample #{open_count}")
            elif key == ord('c') and landmarks:
                crop = cropper.crop_eye(frame, landmarks.get("left_eye"))
                if crop is not None:
                    closed_count += 1
                    cv2.imwrite(str(closed_dir / f"closed_{closed_count:04d}.png"), crop)
                    print(f"Captured Closed sample #{closed_count}")

    finally:
        cam.stop()
        cv2.destroyAllWindows()
        print(f"Collection done! Total Open: {open_count}, Total Closed: {closed_count}")


if __name__ == "__main__":
    collect_samples()
