import sys
import time
from pathlib import Path
import cv2

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from vision.ml.predictor import GazeDirectionPredictor, EyeStatePredictor


def test_image(image_path: str = None):
    print("=" * 60)
    print("EyeSpeak AI - Single Image Prediction Tester")
    print("=" * 60)

    # If no image path provided, use a sample from the Mendeley dataset
    if not image_path:
        sample_candidates = list(Path("database/datasets/raw/eye_tracker_data").rglob("*.jpg"))
        if sample_candidates:
            image_path = str(sample_candidates[0])
            print(f"No image supplied. Using sample from dataset: {image_path}")
        else:
            print("Error: No image path supplied and no dataset samples found.")
            return

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Unable to load image from {image_path}")
        return

    gaze_predictor = GazeDirectionPredictor()
    eye_state_predictor = EyeStatePredictor()

    start_time = time.time()
    gaze_pred, gaze_conf = gaze_predictor.predict_with_confidence(img)
    gaze_probs = gaze_predictor.predict_probabilities(img)
    eye_state_pred, eye_state_conf = eye_state_predictor.predict_with_confidence(img)
    elapsed_ms = (time.time() - start_time) * 1000

    print(f"\nResults for: {Path(image_path).name}")
    print(f"----------------------------------------")
    print(f"Predicted Gaze Direction: {gaze_pred} (Confidence: {gaze_conf * 100:.1f}%)")
    print(f"Class Probabilities: {gaze_probs}")
    print(f"Predicted Eye State:      {eye_state_pred} (Confidence: {eye_state_conf * 100:.1f}%)")
    print(f"Inference Latency:        {elapsed_ms:.2f} ms")
    print("=" * 60)


if __name__ == "__main__":
    img_arg = sys.argv[1] if len(sys.argv) > 1 else None
    test_image(img_arg)
