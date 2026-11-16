import os
import sys
import json
import hashlib
from pathlib import Path
from collections import Counter
import cv2


def inspect_dataset(root_path: Path, dataset_name: str) -> dict:
    print(f"\n==========================================", flush=True)
    print(f"Scanning {dataset_name} at: {root_path}", flush=True)
    print(f"==========================================", flush=True)

    if not root_path.exists():
        return {"status": "MISSING", "error": f"Path {root_path} does not exist."}

    valid_extensions = {".png", ".jpg", ".jpeg", ".bmp"}
    all_files = [p for p in root_path.rglob("*.*") if p.suffix.lower() in valid_extensions]
    total_files = len(all_files)
    print(f"Total image files detected: {total_files}", flush=True)

    class_counts = Counter()
    image_shapes = Counter()
    channels_count = Counter()
    corrupted_count = 0
    hashes = {}
    duplicates = []
    sample_files = []

    for idx, file_path in enumerate(all_files):
        class_name = file_path.parent.name
        class_counts[class_name] += 1

        # Check MD5 hash
        try:
            with open(file_path, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()
                if h in hashes:
                    duplicates.append({
                        "duplicate": str(file_path.relative_to(root_path)),
                        "original": str(hashes[h].relative_to(root_path))
                    })
                else:
                    hashes[h] = file_path
        except Exception:
            corrupted_count += 1
            continue

        # Check OpenCV readability
        try:
            img = cv2.imread(str(file_path))
            if img is None:
                corrupted_count += 1
            else:
                h_img, w_img, c_img = img.shape
                image_shapes[f"{w_img}x{h_img}"] += 1
                channels_count[c_img] += 1
                if idx < 3:
                    sample_files.append({
                        "filename": file_path.name,
                        "class": class_name,
                        "resolution": f"{w_img}x{h_img}",
                        "channels": c_img
                    })
        except Exception:
            corrupted_count += 1

        if (idx + 1) % 2500 == 0 or (idx + 1) == total_files:
            print(f"[{dataset_name}] Processed {idx + 1}/{total_files} images...", flush=True)

    result = {
        "dataset_name": dataset_name,
        "root_directory": str(root_path),
        "status": "VERIFIED" if corrupted_count == 0 else "PARTIAL_CORRUPT",
        "total_files": total_files,
        "readable_images": total_files - corrupted_count,
        "corrupted_images": corrupted_count,
        "exact_duplicates": len(duplicates),
        "class_distribution": dict(class_counts),
        "top_resolutions": dict(image_shapes.most_common(5)),
        "color_channels": dict(channels_count),
        "sample_files": sample_files
    }
    return result


def main():
    report = {
        "project": "EyeSpeak AI",
        "task": "Phase 1 & Phase 2 Dataset Inspection and Validation",
        "datasets": {}
    }

    # 1. Inspect Kayvan Shah Eye Dataset (archive)
    archive_dir = Path("database/datasets/raw/archive")
    report["datasets"]["kayvan_shah_archive"] = inspect_dataset(archive_dir, "Kayvan Shah Eye Dataset")

    # 2. Inspect Mendeley Eye Gaze Dataset (eye_tracker_data)
    et_dir = Path("database/datasets/raw/eye_tracker_data")
    report["datasets"]["mendeley_eye_tracker"] = inspect_dataset(et_dir, "Mendeley Eye Gaze Dataset")

    # 3. Inspect Mohan K. Jha Step-1
    step1_dir = Path("database/datasets/raw/step-1-detect-open-and-closed-eye")
    step1_ipynb = Path("database/datasets/raw/step-1-detect-open-and-closed-eye.ipynb")

    if step1_dir.exists() and any(step1_dir.iterdir()):
        report["datasets"]["mohan_k_jha_step1"] = inspect_dataset(step1_dir, "Mohan K. Jha Open/Closed Dataset")
    else:
        print("\n==========================================", flush=True)
        print("Checking Mohan K. Jha Step-1 Dataset Directory", flush=True)
        print("==========================================", flush=True)
        has_ipynb = step1_ipynb.exists()
        print(f"Directory 'database/datasets/raw/step-1-detect-open-and-closed-eye' exists: {step1_dir.exists()}", flush=True)
        print(f"Notebook 'step-1-detect-open-and-closed-eye.ipynb' exists: {has_ipynb}", flush=True)
        report["datasets"]["mohan_k_jha_step1"] = {
            "dataset_name": "Mohan K. Jha Open/Closed Dataset",
            "status": "NOTEBOOK_FILE_ONLY_IMAGE_FOLDER_MISSING",
            "directory_path": str(step1_dir),
            "notebook_file": str(step1_ipynb) if has_ipynb else None,
            "error": "The file 'step-1-detect-open-and-closed-eye.ipynb' is a Jupyter notebook code script, not an image folder. The code references '/kaggle/input/mrl-dataset/train/Open_Eyes' and 'Closed_Eyes', but the raw image folder was not provided in raw/step-1-detect-open-and-closed-eye/."
        }

    manifests_dir = Path("database/datasets/manifests")
    manifests_dir.mkdir(parents=True, exist_ok=True)
    report_path = manifests_dir / "dataset_validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[Success] Dataset validation report written to {report_path}", flush=True)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
