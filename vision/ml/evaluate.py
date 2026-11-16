import time
from typing import Dict, Any
from sklearn.metrics import accuracy_score, f1_score
from vision.ml.dataset_loader import DatasetLoader
from vision.ml.preprocessing import PreprocessingPipeline
from vision.ml.train_random_forest import train_random_forest
from vision.ml.train_svm import train_svm
from vision.ml.train_extra_trees import train_extra_trees


def evaluate_models() -> Dict[str, Any]:
    """Benchmarks Random Forest, Extra Trees, and SVM classifiers."""
    print("\n" + "=" * 60)
    print("Evaluating Model Architectures for EyeSpeak AI")
    print("=" * 60)

    loader = DatasetLoader()
    X, y = loader.load_or_generate_dataset()

    pipeline = PreprocessingPipeline()
    X_train, _, X_test, y_train, _, y_test = pipeline.split_data(X, y)
    X_train_scaled = pipeline.fit_transform(X_train)
    X_test_scaled = pipeline.transform(X_test)

    results = {}

    models = {
        "Random Forest": train_random_forest(artifact_path="vision/artifacts/random_forest_eye_model.joblib"),
        "Extra Trees": train_extra_trees(artifact_path="vision/artifacts/extra_trees_eye_model.joblib"),
        "SVM (RBF)": train_svm(artifact_path="vision/artifacts/svm_eye_model.joblib")
    }

    for name, model in models.items():
        # Inference speed benchmark (100 samples)
        start_time = time.time()
        preds = model.predict(X_test_scaled)
        latency_ms = ((time.time() - start_time) / len(X_test_scaled)) * 1000

        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds)

        results[name] = {
            "Accuracy": round(acc * 100, 2),
            "F1-Score": round(f1, 4),
            "Latency_per_frame_ms": round(latency_ms, 3)
        }

    print("\n" + "-" * 55)
    print(f"{'Model':<18} | {'Accuracy':<10} | {'F1-Score':<10} | {'Latency (ms)':<12}")
    print("-" * 55)
    for model_name, metrics in results.items():
        print(f"{model_name:<18} | {metrics['Accuracy']}%{'':<4} | {metrics['F1-Score']:<10} | {metrics['Latency_per_frame_ms']:<12}")
    print("-" * 55)
    return results


if __name__ == "__main__":
    evaluate_models()
