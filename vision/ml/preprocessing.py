from typing import Tuple
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib


class PreprocessingPipeline:
    """Handles train/test splitting and feature standardization."""

    def __init__(self):
        self.scaler = StandardScaler()

    def split_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2,
        val_size: float = 0.1,
        random_state: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        # Split train + val vs test
        X_train_val, X_test, y_train_val, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        # Split train vs val
        val_relative = val_size / (1.0 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_val, y_train_val, test_size=val_relative, random_state=random_state, stratify=y_train_val
        )
        return X_train, X_val, X_test, y_train, y_val, y_test

    def fit_transform(self, X_train: np.ndarray) -> np.ndarray:
        return self.scaler.fit_transform(X_train)

    def transform(self, X: np.ndarray) -> np.ndarray:
        return self.scaler.transform(X)

    def save_scaler(self, path: str = "vision/artifacts/scaler.joblib"):
        joblib.dump(self.scaler, path)

    @classmethod
    def load_scaler(cls, path: str = "vision/artifacts/scaler.joblib"):
        pipeline = cls()
        pipeline.scaler = joblib.load(path)
        return pipeline
