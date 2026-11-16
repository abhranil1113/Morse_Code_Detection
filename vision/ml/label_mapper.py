"""
Label Mapper for EyeSpeak AI Datasets.
Provides explicit semantic mappings for Eye State (OPEN/CLOSED) and Gaze Direction (CENTER/LEFT/RIGHT/UP/DOWN).
Enforces separation of concerns: Kayvan Shah 'close_look' is NEVER mapped to eye state CLOSED.
"""

from typing import Dict, Optional, List

# Target Label Sets
TARGET_EYE_STATE_CLASSES = ["CLOSED", "OPEN"]
TARGET_GAZE_CLASSES = ["CENTER", "LEFT", "RIGHT", "UP", "DOWN"]

# Model 1: Eye State Mapping
EYE_STATE_MAP = {
    "closed": 0,
    "closed_eyes": 0,
    "close": 0,
    "open": 1,
    "open_eyes": 1
}

# Model 2: Mendeley Eye Gaze Dataset Mapping
# Maps the 5 balanced classes into standardized uppercase targets
MENDELEY_GAZE_MAP = {
    "straight": "CENTER",
    "left": "LEFT",
    "right": "RIGHT",
    "up": "UP",
    "down": "DOWN"
}

# Model 2: Kayvan Shah Eye Dataset Mapping
# Strictly maps horizontal & center gaze.
# 'close_look' is ignored for gaze direction to prevent corrupting target semantics.
KAYVAN_GAZE_MAP = {
    "forward_look": "CENTER",
    "left_look": "LEFT",
    "right_look": "RIGHT",
    "close_look": None  # Excluded from gaze direction classification
}

GAZE_TO_INT: Dict[str, int] = {
    "CENTER": 0,
    "LEFT": 1,
    "RIGHT": 2,
    "UP": 3,
    "DOWN": 4
}

INT_TO_GAZE: Dict[int, str] = {v: k for k, v in GAZE_TO_INT.items()}
INT_TO_EYE_STATE: Dict[int, str] = {0: "CLOSED", 1: "OPEN"}


class LabelMapper:
    @staticmethod
    def map_mendeley_label(raw_class: str) -> Optional[int]:
        normalized = raw_class.strip().lower()
        target_name = MENDELEY_GAZE_MAP.get(normalized)
        if target_name is not None and target_name in GAZE_TO_INT:
            return GAZE_TO_INT[target_name]
        return None

    @staticmethod
    def map_kayvan_label(raw_class: str) -> Optional[int]:
        normalized = raw_class.strip().lower()
        target_name = KAYVAN_GAZE_MAP.get(normalized)
        if target_name is not None and target_name in GAZE_TO_INT:
            return GAZE_TO_INT[target_name]
        return None

    @staticmethod
    def map_eye_state_label(raw_class: str) -> Optional[int]:
        normalized = raw_class.strip().lower()
        return EYE_STATE_MAP.get(normalized)
