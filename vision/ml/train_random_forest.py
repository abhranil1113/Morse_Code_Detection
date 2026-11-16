import os
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, roc_auc_score
import joblib
from vision.ml.dataset_loader import DatasetLoader
from vision.ml.preprocessing import PreprocessingPipeline


def train_random_forest(
    n_estimators: int = 150,
    max_depth: int = 20,
    min_samples_split: int = 4,
    artifact_path: str = "vision/artifacts/random_forest_eye_model.joblib"
) -> RandomForestClassifier:
    """Trains a Random Forest classifier on HOG eye features for open/closed eye state."""
    print("=" * 60)
    print("Starting Random Forest Model Training")
    print("=" * 60)

    # 1. Load Data
    loader = DatasetLoader()
    X, y = loader.load_or_generate_dataset()

    # 2. Preprocess & Split
    pipeline = PreprocessingPipeline()
    X_train, X_val, X_test, y_train, y_val, y_test = pipeline.split_data(X, y)

    X_train_scaled = pipeline.fit_transform(X_train)
    X_val_scaled = pipeline.transform(X_val)
    X_test_scaled = pipeline.transform(X_test)

    # 3. Model Definition
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced"
    )

    print(f"Training on {len(X_train)} samples with {X_train.shape[1]} features...")
    clf.fit(X_train_scaled, y_train)

    # 4. Evaluation
    val_preds = clf.predict(X_val_scaled)
    val_acc = accuracy_score(y_val, val_preds)
    print(f"\n[Validation Set Accuracy]: {val_acc * 100:.2f}%")

    test_preds = clf.predict(X_test_scaled)
    test_acc = accuracy_score(y_test, test_preds)
    test_auc = roc_auc_score(y_test, clf.predict_proba(X_test_scaled)[:, 1])
    print(f"[Test Set Accuracy]: {test_acc * 100:.2f}% | [ROC-AUC]: {test_auc:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, test_preds, target_names=["Closed", "Open"]))

    # 5. Persist Model and Scaler
    Path(artifact_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, artifact_path)
    pipeline.save_scaler("vision/artifacts/scaler.joblib")
    print(f"[Success] Model saved to {artifact_path}")
    return clf


if __name__ == "__main__":
    train_random_forest()
