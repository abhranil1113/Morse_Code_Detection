from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np
import joblib

from vision.ml.feature_extractor import FeatureExtractor
from vision.ml.model_config import GAZE_MODEL_ARTIFACT, EYE_STATE_MODEL_ARTIFACT
from vision.ml.label_mapper import INT_TO_GAZE, INT_TO_EYE_STATE, TARGET_GAZE_CLASSES, TARGET_EYE_STATE_CLASSES


class EyeStatePredictor:
    """
    Predicts eye state (OPEN / CLOSED / UNKNOWN) fusing trained Random Forest appearance features
    with geometric Eye Aspect Ratio (EAR) evidence.
    """

    def __init__(
        self,
        model_path: str = EYE_STATE_MODEL_ARTIFACT,
        ear_closed_threshold: float = 0.18,
        ear_open_threshold: float = 0.27,
        ml_weight: float = 0.50,
        ear_weight: float = 0.50,
        decision_threshold: float = 0.50
    ):
        self.model_path = Path(model_path)
        self.ear_closed_threshold = ear_closed_threshold
        self.ear_open_threshold = ear_open_threshold
        self.ml_weight = ml_weight
        self.ear_weight = ear_weight
        self.decision_threshold = decision_threshold

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
        """Returns string prediction: 'OPEN', 'CLOSED', or 'UNKNOWN'."""
        pred_label, _ = self.predict_with_confidence(image)
        return pred_label

    def predict_with_confidence(
        self,
        image: Optional[np.ndarray],
        ear_value: Optional[float] = None
    ) -> Tuple[str, float]:
        """
        Predicts eye state fusing trained Random Forest appearance features
        with geometric Eye Aspect Ratio (EAR) for robust real-time tracking.
        Returns:
            (predicted_class, confidence_score) where predicted_class is 'OPEN', 'CLOSED', or 'UNKNOWN'
        """
        has_image = image is not None and hasattr(image, "size") and image.size > 0 and len(image.shape) >= 2
        has_ear = ear_value is not None and np.isfinite(ear_value) and 0.0 <= ear_value <= 1.5

        # Return UNKNOWN when no valid eye evidence is available
        if not has_image and not has_ear:
            return "UNKNOWN", 0.0

        ml_prob_closed: Optional[float] = None
        if self.model is not None and has_image:
            try:
                feats = self.extractor.extract_features(image).reshape(1, -1)
                probs = self.model.predict_proba(feats)[0]
                # classes_ are [0 (CLOSED), 1 (OPEN)]
                ml_prob_closed = float(probs[0])
            except Exception:
                ml_prob_closed = None

        ear_prob_closed: Optional[float] = None
        if has_ear:
            # Physical EAR: below closed threshold indicates closure; above open threshold indicates open
            if ear_value <= self.ear_closed_threshold:
                ear_prob_closed = min(1.0, 0.75 + (self.ear_closed_threshold - ear_value) * 2.0)
            elif ear_value >= self.ear_open_threshold:
                ear_prob_closed = max(0.0, 0.20 - (ear_value - self.ear_open_threshold) * 1.5)
            else:
                span = self.ear_open_threshold - self.ear_closed_threshold
                ear_prob_closed = (self.ear_open_threshold - ear_value) / (span if span > 1e-4 else 0.09)

        # Fused decision
        if ml_prob_closed is not None and ear_prob_closed is not None:
            # Check disagreement between ML appearance and EAR geometry
            disagreement = abs(ml_prob_closed - ear_prob_closed)
            prob_closed = self.ml_weight * ml_prob_closed + self.ear_weight * ear_prob_closed
            confidence_damping = disagreement * 0.15
        elif ml_prob_closed is not None:
            prob_closed = ml_prob_closed
            confidence_damping = 0.0
        elif ear_prob_closed is not None:
            prob_closed = ear_prob_closed
            confidence_damping = 0.0
        else:
            return "UNKNOWN", 0.0

        if prob_closed >= self.decision_threshold:
            conf = min(1.0, max(0.50, prob_closed - confidence_damping))
            return "CLOSED", round(conf, 3)
        else:
            conf = min(1.0, max(0.50, (1.0 - prob_closed) - confidence_damping))
            return "OPEN", round(conf, 3)

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
