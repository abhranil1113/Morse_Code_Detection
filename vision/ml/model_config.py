from dataclasses import dataclass
from typing import Tuple


@dataclass
class PreprocessingConfig:
    target_size: Tuple[int, int] = (64, 64)
    grayscale: bool = True
    equalize_hist: bool = True


@dataclass
class HOGConfig:
    win_size: Tuple[int, int] = (64, 64)
    block_size: Tuple[int, int] = (16, 16)
    block_stride: Tuple[int, int] = (8, 8)
    cell_size: Tuple[int, int] = (8, 8)
    nbins: int = 9


@dataclass
class RandomForestConfig:
    n_estimators: int = 150
    max_depth: int = 25
    min_samples_split: int = 4
    min_samples_leaf: int = 2
    random_state: int = 42
    n_jobs: int = -1
    class_weight: str = "balanced"


# Paths
RAW_ARCHIVE_PATH = "database/datasets/raw/archive"
RAW_MENDELEY_PATH = "database/datasets/raw/eye_tracker_data"
RAW_STEP1_PATH = "database/datasets/raw/step-1-detect-open-and-closed-eye"

PROCESSED_GAZE_DIR = "database/datasets/processed/gaze_direction"
PROCESSED_EYE_STATE_DIR = "database/datasets/processed/eye_state"

GAZE_MODEL_ARTIFACT = "vision/artifacts/gaze_direction_random_forest.joblib"
EYE_STATE_MODEL_ARTIFACT = "vision/artifacts/eye_state_random_forest.joblib"
GAZE_METADATA_ARTIFACT = "vision/artifacts/metadata/gaze_direction_metadata.json"
EYE_STATE_METADATA_ARTIFACT = "vision/artifacts/metadata/eye_state_metadata.json"
