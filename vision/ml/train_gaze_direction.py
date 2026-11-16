import os
import sys
import json
import time
import hashlib
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from collections import Counter
import numpy as np
import cv2
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
import joblib

from vision.ml.label_mapper import LabelMapper, TARGET_GAZE_CLASSES, GAZE_TO_INT, INT_TO_GAZE
from vision.ml.feature_extractor import FeatureExtractor
from vision.ml.model_config import (
    RAW_MENDELEY_PATH,
    RAW_ARCHIVE_PATH,
    GAZE_MODEL_ARTIFACT,
    GAZE_METADATA_ARTIFACT,
    RandomForestConfig
)


def load_mendeley_gaze_data(data_dir: Path, extractor: FeatureExtractor):
    """Loads all 5 classes from Mendeley dataset and extracts HOG features."""
    print(f"\n[Data Loader] Loading Mendeley Eye Gaze dataset from {data_dir}...", flush=True)
    X = []
    y = []
    filepaths = []
    hashes = {}
    duplicates = []

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    all_files = [p for p in data_dir.rglob("*.*") if p.suffix.lower() in valid_exts]

    print(f"Total candidate images: {len(all_files)}", flush=True)

    for idx, p in enumerate(all_files):
        raw_class = p.parent.name
        label_int = LabelMapper.map_mendeley_label(raw_class)
        if label_int is None:
            continue

        # Check MD5 for duplicate-aware tracking
        with open(p, "rb") as f:
            h = hashlib.md5(f.read()).hexdigest()
            if h in hashes:
                duplicates.append(str(p))
                # Skip duplicate to prevent data leakage across splits
                continue
            else:
                hashes[h] = str(p)

        img = cv2.imread(str(p))
        if img is None:
            continue

        feats = extractor.extract_features(img)
        X.append(feats)
        y.append(label_int)
        filepaths.append(str(p))

        if (idx + 1) % 1500 == 0:
            print(f"Extracted HOG features for {idx + 1}/{len(all_files)} images...", flush=True)

    print(f"Loaded {len(X)} deduplicated samples (skipped {len(duplicates)} duplicates).", flush=True)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64), len(duplicates)


def train_gaze_model():
    print("=" * 70, flush=True)
    print("Starting Training: Model 2 - Eye Gaze Direction (5 Classes)", flush=True)
    print("Target Classes: [CENTER, LEFT, RIGHT, UP, DOWN]", flush=True)
    print("=" * 70, flush=True)

    extractor = FeatureExtractor()
    mendeley_dir = Path(RAW_MENDELEY_PATH)
    if not mendeley_dir.exists():
        print(f"Error: {mendeley_dir} not found. Please extract eye_tracker_data.zip first.", flush=True)
        return

    # 1. Feature Extraction & Deduplication
    X, y, num_dupes = load_mendeley_gaze_data(mendeley_dir, extractor)
    print(f"\nFeature matrix shape: {X.shape}, Labels shape: {y.shape}", flush=True)

    # Verify all 5 classes are present
    unique_classes, counts = np.unique(y, return_counts=True)
    print("Class Distribution in Cleaned Dataset:")
    for cls_int, count in zip(unique_classes, counts):
        print(f"  - {INT_TO_GAZE[cls_int]}: {count} samples", flush=True)

    assert len(unique_classes) == 5, f"Expected 5 classes, found {len(unique_classes)}"

    # 2. Stratified Data Splitting (70% Train, 15% Val, 15% Test)
    print("\nSplitting dataset into 70% Train, 15% Validation, 15% Test...", flush=True)
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=(0.15 / 0.85), random_state=42, stratify=y_train_val
    )

    print(f"Train set: {len(X_train)} samples | Val set: {len(X_val)} samples | Test set: {len(X_test)} samples", flush=True)

    # 3. Model Definition & Training
    rf_cfg = RandomForestConfig(n_estimators=150, max_depth=25, min_samples_split=4, random_state=42)
    clf = RandomForestClassifier(
        n_estimators=rf_cfg.n_estimators,
        max_depth=rf_cfg.max_depth,
        min_samples_split=rf_cfg.min_samples_split,
        min_samples_leaf=rf_cfg.min_samples_leaf,
        random_state=rf_cfg.random_state,
        n_jobs=rf_cfg.n_jobs,
        class_weight=rf_cfg.class_weight
    )

    print("\nTraining RandomForestClassifier on HOG feature vectors...", flush=True)
    start_time = time.time()
    clf.fit(X_train, y_train)
    train_duration = time.time() - start_time
    print(f"Training completed in {train_duration:.2f} seconds.", flush=True)

    # 4. Validation Evaluation
    val_preds = clf.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)
    val_f1 = f1_score(y_val, val_preds, average="macro")
    print(f"\n[Validation Set Performance]:", flush=True)
    print(f"Accuracy: {val_acc * 100:.2f}% | Macro F1-Score: {val_f1:.4f}", flush=True)

    # 5. Final Unseen Test Set Evaluation
    start_infer = time.time()
    test_preds = clf.predict(X_test)
    total_infer_time = time.time() - start_infer
    avg_latency_ms = (total_infer_time / len(X_test)) * 1000

    test_acc = accuracy_score(y_test, test_preds)
    test_f1 = f1_score(y_test, test_preds, average="macro")
    print(f"\n[Final Test Set Performance]:", flush=True)
    print(f"Test Accuracy: {test_acc * 100:.2f}%", flush=True)
    print(f"Macro F1-Score: {test_f1:.4f}", flush=True)
    print(f"Average Inference Latency: {avg_latency_ms:.3f} ms / frame", flush=True)

    target_names = [INT_TO_GAZE[i] for i in range(5)]
    report_str = classification_report(y_test, test_preds, target_names=target_names)
    print("\nClassification Report:\n" + report_str, flush=True)

    cm = confusion_matrix(y_test, test_preds).tolist()
    print("Confusion Matrix:\n", np.array(cm), flush=True)

    # 6. Save Artifacts & Reports
    Path(GAZE_MODEL_ARTIFACT).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, GAZE_MODEL_ARTIFACT)
    print(f"\nTrained model persisted to: {GAZE_MODEL_ARTIFACT}", flush=True)

    # Save Metadata
    Path(GAZE_METADATA_ARTIFACT).parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "model_type": "RandomForestClassifier",
        "target_task": "Eye Gaze Direction Classification (5 classes)",
        "classes": TARGET_GAZE_CLASSES,
        "class_to_int": GAZE_TO_INT,
        "int_to_class": INT_TO_GAZE,
        "train_samples": int(len(X_train)),
        "val_samples": int(len(X_val)),
        "test_samples": int(len(X_test)),
        "total_deduplicated_samples": int(len(X)),
        "skipped_exact_duplicates": int(num_dupes),
        "test_accuracy": round(float(test_acc), 4),
        "test_macro_f1": round(float(test_f1), 4),
        "inference_latency_ms": round(float(avg_latency_ms), 3),
        "feature_dim": int(extractor.feature_dim),
        "hyperparameters": {
            "n_estimators": rf_cfg.n_estimators,
            "max_depth": rf_cfg.max_depth,
            "min_samples_split": rf_cfg.min_samples_split,
            "class_weight": rf_cfg.class_weight
        }
    }
    with open(GAZE_METADATA_ARTIFACT, "w") as f:
        json.dump(metadata, f, indent=2)

    # Save detailed evaluation report
    report_dir = Path("vision/reports/gaze_direction")
    report_dir.mkdir(parents=True, exist_ok=True)
    with open(report_dir / "evaluation_report.txt", "w") as f:
        f.write("EyeSpeak AI - Model 2: Gaze Direction Evaluation Report\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Test Accuracy: {test_acc * 100:.2f}%\n")
        f.write(f"Macro F1-Score: {test_f1:.4f}\n")
        f.write(f"Inference Latency: {avg_latency_ms:.3f} ms / frame\n\n")
        f.write("Classification Report:\n")
        f.write(report_str + "\n\n")
        f.write(f"Confusion Matrix (Rows=True, Cols=Pred, Classes={target_names}):\n")
        f.write(str(np.array(cm)) + "\n")

    with open(report_dir / "metrics.json", "w") as f:
        json.dump({
            "test_accuracy": test_acc,
            "macro_f1": test_f1,
            "inference_latency_ms": avg_latency_ms,
            "confusion_matrix": cm,
            "classes": target_names
        }, f, indent=2)

    print(f"Reports saved under {report_dir}/", flush=True)


if __name__ == "__main__":
    train_gaze_model()
