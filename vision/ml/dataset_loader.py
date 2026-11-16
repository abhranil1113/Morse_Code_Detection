import os
from pathlib import Path
from typing import Tuple, List
import numpy as np
import cv2
from vision.features.hog_extractor import HOGFeatureExtractor


class DatasetLoader:
    """Loads raw eye images from database/datasets and extracts feature matrices for training."""

    def __init__(self, raw_data_dir: str = "database/datasets/raw/mrl_eye"):
        self.raw_data_dir = Path(raw_data_dir)
        self.hog_extractor = HOGFeatureExtractor()

    def load_or_generate_dataset(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Loads dataset from raw folder. If raw folders are empty,
        generates synthetic training samples to allow immediate smoke testing and pipeline verification.
        """
        X_list: List[np.ndarray] = []
        y_list: List[int] = []

        closed_dir = self.raw_data_dir / "closed"
        open_dir = self.raw_data_dir / "open"

        has_data = (
            closed_dir.exists() and any(closed_dir.iterdir()) and
            open_dir.exists() and any(open_dir.iterdir())
        )

        if has_data:
            print(f"[DatasetLoader] Found images in {self.raw_data_dir}. Processing...")
            # 0 = closed, 1 = open
            for label, folder in [(0, closed_dir), (1, open_dir)]:
                for file_path in folder.glob("*.*"):
                    if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                        img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            img_resized = cv2.resize(img, (32, 32))
                            feats = self.hog_extractor.extract(img_resized)
                            X_list.append(feats)
                            y_list.append(label)

            X = np.array(X_list, dtype=np.float32)
            y = np.array(y_list, dtype=np.int64)
            print(f"[DatasetLoader] Loaded {len(X)} samples from raw dataset.")
            return X, y

        # Fallback synthetic data generator for pipeline bootstrap
        print(f"[DatasetLoader] Notice: Raw images not yet downloaded to {self.raw_data_dir}.")
        print("[DatasetLoader] Bootstrapping synthetic dataset for initial model structure validation.")
        n_samples = 400
        feat_dim = self.hog_extractor.feature_dim

        # Closed eyes: lower intensity gradient, specific simulated HOG pattern
        X_closed = np.random.normal(loc=0.15, scale=0.05, size=(n_samples // 2, feat_dim))
        y_closed = np.zeros(n_samples // 2, dtype=np.int64)

        # Open eyes: higher edge gradients, prominent circular pupil edges
        X_open = np.random.normal(loc=0.55, scale=0.08, size=(n_samples // 2, feat_dim))
        y_open = np.ones(n_samples // 2, dtype=np.int64)

        X = np.vstack([X_closed, X_open]).astype(np.float32)
        y = np.concatenate([y_closed, y_open])

        indices = np.random.permutation(len(X))
        return X[indices], y[indices]
