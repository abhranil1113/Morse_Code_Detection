from pathlib import Path
from sklearn.svm import SVC
from sklearn.metrics import classification_report, accuracy_score
import joblib
from vision.ml.dataset_loader import DatasetLoader
from vision.ml.preprocessing import PreprocessingPipeline


def train_svm(
    c: float = 1.0,
    kernel: str = "rbf",
    artifact_path: str = "vision/artifacts/svm_eye_model.joblib"
) -> SVC:
    """Trains a Support Vector Machine (RBF Kernel) classifier."""
    print("=" * 60)
    print("Starting SVM Classifier Training")
    print("=" * 60)

    loader = DatasetLoader()
    X, y = loader.load_or_generate_dataset()

    pipeline = PreprocessingPipeline()
    X_train, X_val, X_test, y_train, y_val, y_test = pipeline.split_data(X, y)

    X_train_scaled = pipeline.fit_transform(X_train)
    X_test_scaled = pipeline.transform(X_test)

    clf = SVC(C=c, kernel=kernel, probability=True, random_state=42)
    clf.fit(X_train_scaled, y_train)

    test_preds = clf.predict(X_test_scaled)
    test_acc = accuracy_score(y_test, test_preds)
    print(f"\n[SVM Test Accuracy]: {test_acc * 100:.2f}%")
    print(classification_report(y_test, test_preds, target_names=["Closed", "Open"]))

    Path(artifact_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, artifact_path)
    return clf


if __name__ == "__main__":
    train_svm()
