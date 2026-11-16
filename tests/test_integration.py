import os
from pathlib import Path


def test_directory_structure_exists():
    required_paths = [
        "database/datasets/raw/mrl_eye",
        "database/datasets/raw/eye_direction",
        "database/datasets/raw/mpiigaze",
        "database/datasets/raw/webcam_samples",
        "database/datasets/processed/eye_crops",
        "database/datasets/processed/features",
        "database/datasets/manifests/dataset_metadata.json",
        "backend/app/main.py",
        "backend/app/db/db_connection.py",
        "backend/app/db/schema.py",
        "backend/app/models/user.py",
        "backend/app/modules/auth/service.py",
        "backend/app/modules/rooms/service.py",
        "backend/app/modules/messages/service.py",
        "vision/camera/opencv_camera.py",
        "vision/ml/train_random_forest.py",
        "vision/morse/blink_detector.py",
        "vision/morse/decoder.py",
        "vision/gestures/gaze_controller.py",
        "vision/events/event_emitter.py",
        "vision/communication/ws_client.py",
        "vision/agent/local_bridge.py",
        "frontend/src/main.tsx",
        "requirements.txt",
        ".env",
        ".env.example",
        "docker-compose.yml",
        "docs/API_DOCUMENTATION.md"
    ]

    for p in required_paths:
        assert Path(p).exists(), f"Missing required file or directory: {p}"
    print("Verification Successful: All required directories and files exist!")


if __name__ == "__main__":
    test_directory_structure_exists()
