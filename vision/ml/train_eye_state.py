import os
import sys
import json
import time
import hashlib
from pathlib import Path
from collections import Counter
from typing import Optional, List, Dict
import numpy as np
import cv2
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from vision.ml.label_mapper import LabelMapper, TARGET_EYE_STATE_CLASSES, INT_TO_EYE_STATE
from vision.ml.feature_extractor import FeatureExtractor
from vision.ml.model_config import (
    RAW_STEP1_PATH,
    EYE_STATE_MODEL_ARTIFACT,
    EYE_STATE_METADATA_ARTIFACT,
    RandomForestConfig
)


def check_eye_state_dataset(data_dir: Path) -> bool:
    """Verifies whether a raw eye dataset folder exists and contains open and closed images."""
    if not data_dir.exists():
        return False
    valid_exts = {".png", ".jpg", ".jpeg", ".bmp"}
    img_files = [p for p in data_dir.rglob("*.*") if p.suffix.lower() in valid_exts]
    return len(img_files) > 100


def get_eye_state_label(folder_name: str) -> Optional[int]:
    """
    Maps folder name to 0 (CLOSED) or 1 (OPEN).
    Gaze-direction labels (e.g. 'close_look', 'forward_look', 'straight') are strictly excluded
    to prevent cross-task semantic contamination.
    """
    name = folder_name.strip().lower()
    if name in ["closed", "close", "closed_eyes"]:
        return 0
    elif name in ["open", "open_eyes"]:
        return 1
    return None


def train_eye_state_model():
    print("=" * 70, flush=True)
    print("Starting Training: Model 1 - Eye State Classification (OPEN / CLOSED)", flush=True)
    print("Target Classes: [CLOSED (0), OPEN (1)]", flush=True)
    print("=" * 70, flush=True)

    candidates = [
        Path("database/datasets/raw/mrl_eye"),
        Path("database/datasets/raw/archive/Eye dataset"),
        Path(RAW_STEP1_PATH)
    ]

    dataset_dir = None
    for cand in candidates:
        if cand.exists() and check_eye_state_dataset(cand):
            dataset_dir = cand
            break

    if dataset_dir is None:
        print("\n[Error] No eye state images found in candidate directories.", flush=True)
        return

    print(f"Loading eye state dataset from: {dataset_dir}", flush=True)
    extractor = FeatureExtractor()
    X, y = [], []
    valid_exts = {".jpg", ".jpeg", ".png", ".bmp"}

    # Load balanced sample per class (up to 1500 per class for rapid, robust training)
    samples_per_class = {0: 0, 1: 0}
    max_per_class = 1800

    for p in dataset_dir.rglob("*.*"):
        if p.suffix.lower() not in valid_exts:
            continue
        label = get_eye_state_label(p.parent.name)
        if label is None:
            continue
        if samples_per_class[label] >= max_per_class:
            continue

        img = cv2.imread(str(p))
        if img is not None:
            feats = extractor.extract_features(img)
            X.append(feats)
            y.append(label)
            samples_per_class[label] += 1

    print(f"Loaded {len(X)} balanced samples: CLOSED={samples_per_class[0]}, OPEN={samples_per_class[1]}", flush=True)

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int64)

    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=(0.15 / 0.85), random_state=42, stratify=y_train_val
    )

    print(f"Dataset split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}", flush=True)
    print("Training Random Forest Classifier (n_estimators=100, max_depth=20)...", flush=True)

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=20,
        min_samples_split=4,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1
    )
    clf.fit(X_train, y_train)

    val_preds = clf.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)

    test_preds = clf.predict(X_test)
    test_acc = accuracy_score(y_test, test_preds)
    test_f1 = f1_score(y_test, test_preds, average="macro")

    print(f"Validation Accuracy: {val_acc * 100:.2f}%", flush=True)
    print(f"Test Accuracy:       {test_acc * 100:.2f}%", flush=True)
    print(f"Test F1-Score:       {test_f1:.4f}", flush=True)
    print("\nClassification Report:\n", classification_report(y_test, test_preds, target_names=["CLOSED", "OPEN"]), flush=True)

    # Save model artifact
    Path(EYE_STATE_MODEL_ARTIFACT).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, EYE_STATE_MODEL_ARTIFACT)
    print(f"[Success] Saved trained Random Forest model to: {EYE_STATE_MODEL_ARTIFACT}", flush=True)

    # Save metadata artifact
    Path(EYE_STATE_METADATA_ARTIFACT).parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "model_type": "RandomForestClassifier",
        "n_estimators": 100,
        "max_depth": 20,
        "classes": ["CLOSED", "OPEN"],
        "dataset_source": str(dataset_dir),
        "total_samples": len(X),
        "test_accuracy": round(float(test_acc), 4),
        "test_f1": round(float(test_f1), 4),
        "feature_type": "HOG (Histogram of Oriented Gradients)",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(EYE_STATE_METADATA_ARTIFACT, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[Success] Saved metadata artifact to: {EYE_STATE_METADATA_ARTIFACT}", flush=True)


if __name__ == "__main__":
    train_eye_state_model()
