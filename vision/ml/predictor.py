from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np
import joblib

from vision.ml.feature_extractor import FeatureExtractor
from vision.ml.model_config import GAZE_MODEL_ARTIFACT, EYE_STATE_MODEL_ARTIFACT
from vision.ml.label_mapper import INT_TO_GAZE, INT_TO_EYE_STATE, TARGET_GAZE_CLASSES, TARGET_EYE_STATE_CLASSES


class EyeStatePredictor:
    """Predicts eye state (OPEN / CLOSED) from raw eye crops using trained Random Forest."""

    def __init__(self, model_path: str = EYE_STATE_MODEL_ARTIFACT, ear_fallback_threshold: float = 0.22):
        self.model_path = Path(model_path)
        self.ear_fallback_threshold = ear_fallback_threshold
        self.extractor = FeatureExtractor()
        self.model = None
        self._load_model()

    def _load_model(self):
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
            except Exception as e:
                print(f"[EyeStatePredictor] Warning loading model: {e}")

    def predict(self, image: np.ndarray) -> str:
        """Returns string prediction: 'OPEN' or 'CLOSED'."""
        pred_label, _ = self.predict_with_confidence(image)
        return pred_label

    def predict_with_confidence(self, image: np.ndarray, ear_value: Optional[float] = None) -> Tuple[str, float]:
        """
        Returns:
            (predicted_class, confidence_score)
        """
        if (image is None or image.size == 0) and ear_value is None:
            return "UNKNOWN", 0.0

        if self.model is not None and image is not None and image.size > 0:
            try:
                feats = self.extractor.extract_features(image).reshape(1, -1)
                probs = self.model.predict_proba(feats)[0]
                pred_idx = int(np.argmax(probs))
                confidence = float(probs[pred_idx])
                return INT_TO_EYE_STATE.get(pred_idx, "UNKNOWN"), confidence
            except Exception:
                pass

        # Fallback to EAR rule if Model 1 artifact is pending image dataset download
        if ear_value is not None:
            if ear_value < self.ear_fallback_threshold:
                conf = min(1.0, max(0.5, (self.ear_fallback_threshold - ear_value) / self.ear_fallback_threshold + 0.5))
                return "CLOSED", conf
            else:
                conf = min(1.0, max(0.5, (ear_value - self.ear_fallback_threshold) / 0.2 + 0.5))
                return "OPEN", conf

        return "OPEN", 0.5

    def predict_from_crop(self, image: np.ndarray, ear_value: Optional[float] = None) -> Tuple[int, float]:
        """
        Returns integer eye state:
            0 = CLOSED, 1 = OPEN
        along with confidence score float.
        """
        label, conf = self.predict_with_confidence(image, ear_value=ear_value)
        return (0 if label == "CLOSED" else 1), conf



class GazeDirectionPredictor:
    """Predicts 5-class gaze direction (CENTER, LEFT, RIGHT, UP, DOWN) using trained Random Forest."""

    def __init__(self, model_path: str = GAZE_MODEL_ARTIFACT):
        self.model_path = Path(model_path)
        self.extractor = FeatureExtractor()
        self.model = None
        self._load_model()

    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"[GazeDirectionPredictor] Model artifact not found at {self.model_path}. "
                "Please run vision/ml/train_gaze_direction.py first."
            )
        self.model = joblib.load(self.model_path)

    def predict(self, image: np.ndarray) -> str:
        """Returns string prediction: 'CENTER', 'LEFT', 'RIGHT', 'UP', or 'DOWN'."""
        pred_label, _ = self.predict_with_confidence(image)
        return pred_label

    def predict_with_confidence(self, image: np.ndarray) -> Tuple[str, float]:
        if image is None or image.size == 0:
            return "UNKNOWN", 0.0

        feats = self.extractor.extract_features(image).reshape(1, -1)
        probs = self.model.predict_proba(feats)[0]
        pred_idx = int(np.argmax(probs))
        confidence = float(probs[pred_idx])
        return INT_TO_GAZE.get(pred_idx, "UNKNOWN"), confidence

    def predict_probabilities(self, image: np.ndarray) -> Dict[str, float]:
        if image is None or image.size == 0:
            return {cls_name: 0.0 for cls_name in TARGET_GAZE_CLASSES}

        feats = self.extractor.extract_features(image).reshape(1, -1)
        probs = self.model.predict_proba(feats)[0]
        return {INT_TO_GAZE[i]: float(probs[i]) for i in range(len(probs))}
