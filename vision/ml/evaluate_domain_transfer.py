import os
import sys
import json
from pathlib import Path
import numpy as np
import cv2
from sklearn.metrics import classification_report, accuracy_score
import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from vision.ml.label_mapper import LabelMapper, INT_TO_GAZE
from vision.ml.feature_extractor import FeatureExtractor
from vision.ml.model_config import RAW_ARCHIVE_PATH, GAZE_MODEL_ARTIFACT


def evaluate_kayvan_cross_domain():
    print("=" * 70)
    print("Cross-Dataset Domain Shift Evaluation: Kayvan Shah on Mendeley Model")
    print("=" * 70)

    clf = joblib.load(GAZE_MODEL_ARTIFACT)
    extractor = FeatureExtractor()

    archive_dir = Path(RAW_ARCHIVE_PATH) / "Eye dataset"
    if not archive_dir.exists():
        archive_dir = Path(RAW_ARCHIVE_PATH)

    X_kayvan = []
    y_kayvan = []
    classes_evaluated = ["forward_look", "left_look", "right_look"]

    for c in classes_evaluated:
        folder = archive_dir / c
        if not folder.exists():
            continue
        label_int = LabelMapper.map_kayvan_label(c)
        for img_p in list(folder.glob("*.*"))[:500]:  # Sample 500 per class
            img = cv2.imread(str(img_p))
            if img is not None:
                feats = extractor.extract_features(img)
                X_kayvan.append(feats)
                y_kayvan.append(label_int)

    X_kayvan = np.array(X_kayvan, dtype=np.float32)
    y_kayvan = np.array(y_kayvan, dtype=np.int64)

    preds = clf.predict(X_kayvan)
    acc = accuracy_score(y_kayvan, preds)
    print(f"\nEvaluated {len(X_kayvan)} samples from Kayvan Shah dataset.")
    print(f"Zero-Shot Cross-Domain Accuracy: {acc * 100:.2f}%")

    target_names = ["CENTER", "LEFT", "RIGHT"]
    print("\nClassification Report (Kayvan Shah on Mendeley model):\n")
    print(classification_report(y_kayvan, preds, labels=[0, 1, 2], target_names=target_names))

    report_path = Path("vision/reports/gaze_direction/domain_transfer_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "cross_domain_accuracy": round(acc, 4),
            "samples_tested": len(X_kayvan),
            "source_dataset": "Mendeley Eye Gaze Dataset",
            "target_dataset": "Kayvan Shah Eye Dataset",
            "domain_differences": [
                "Bounding box framing: Kayvan Shah features tight bounding box crops of individual eyes (100x100), whereas Mendeley features wider facial region crops (800x600).",
                "Color/Lighting profiles: Different illumination conditions and sensor spectral responses.",
                "Vertical gaze absence: Kayvan Shah lacks UP and DOWN classes entirely, containing only horizontal gaze."
            ]
        }, f, indent=2)

    print(f"Domain transfer report saved to {report_path}")


if __name__ == "__main__":
    evaluate_kayvan_cross_domain()
