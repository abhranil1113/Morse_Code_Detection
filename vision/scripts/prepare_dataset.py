import os
from pathlib import Path
import numpy as np
from vision.ml.dataset_loader import DatasetLoader
from vision.ml.preprocessing import PreprocessingPipeline


def prepare_datasets():
    print("=" * 60)
    print("Preprocessing Raw Datasets -> database/datasets/processed/")
    print("=" * 60)

    loader = DatasetLoader(raw_data_dir="database/datasets/raw/mrl_eye")
    X, y = loader.load_or_generate_dataset()

    pipeline = PreprocessingPipeline()
    X_train, X_val, X_test, y_train, y_val, y_test = pipeline.split_data(X, y)

    out_dir = Path("database/datasets/processed")
    features_dir = out_dir / "features"
    train_dir = out_dir / "train"
    val_dir = out_dir / "validation"
    test_dir = out_dir / "test"

    for d in [features_dir, train_dir, val_dir, test_dir]:
        d.mkdir(parents=True, exist_ok=True)

    np.save(features_dir / "X_features.npy", X)
    np.save(features_dir / "y_labels.npy", y)

    np.save(train_dir / "X_train.npy", X_train)
    np.save(train_dir / "y_train.npy", y_train)

    np.save(val_dir / "X_val.npy", X_val)
    np.save(val_dir / "y_val.npy", y_val)

    np.save(test_dir / "X_test.npy", X_test)
    np.save(test_dir / "y_test.npy", y_test)

    print(f"Dataset preparation complete:")
    print(f" - Train samples: {len(X_train)}")
    print(f" - Val samples:   {len(X_val)}")
    print(f" - Test samples:  {len(X_test)}")
    print(f" - Features saved in {features_dir}")


if __name__ == "__main__":
    prepare_datasets()
