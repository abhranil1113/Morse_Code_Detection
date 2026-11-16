# EyeSpeak AI - Datasets & Data Pipeline

This directory manages both raw training datasets and processed feature matrices for machine learning models (Random Forest, SVM, Extra Trees).

---

## 1. Required Datasets from Kaggle

### Dataset 1: MRL Eye Dataset (Open vs Closed Eyes)
- **Primary Source (Kaggle):** [Drowsiness Dataset (MRL Eye)](https://www.kaggle.com/datasets/dheerajperumandla/drowsiness-dataset) or [MRL Eye Dataset Alternative](https://www.kaggle.com/datasets/prasadvpatil/mrl-dataset)
- **Official Portal:** [http://mrl.cs.vsb.cz/eyedataset](http://mrl.cs.vsb.cz/eyedataset)
- **Target Folder:** `database/datasets/raw/mrl_eye/`
- **Contents:**
  - `database/datasets/raw/mrl_eye/open/` (Images with eyes open)
  - `database/datasets/raw/mrl_eye/closed/` (Images with eyes closed)
- **Usage:**
  Trains the Random Forest / SVM model to classify open vs closed state with high precision under varying illumination, head angles, and glasses.

### Dataset 2: Eye Gaze & Direction Dataset (Left, Right, Center)
- **Primary Source (Kaggle):** [Eye Gaze Dataset](https://www.kaggle.com/datasets/inayat19/eye-gaze-dataset) or [Open & Closed Eyes with Gaze](https://www.kaggle.com/datasets/kayvank/open-and-closed-eyes-dataset)
- **Target Folder:** `database/datasets/raw/eye_direction/`
- **Contents:**
  - `database/datasets/raw/eye_direction/left/`
  - `database/datasets/raw/eye_direction/right/`
  - `database/datasets/raw/eye_direction/center/`
- **Usage:**
  Classifies pupil gaze position for direction-based UI shortcuts and menu selection.

---

## 2. Quick Download via Kaggle CLI

Install the Kaggle CLI:
```bash
pip install kaggle
```

Configure your `~/.kaggle/kaggle.json` API token, then run:

```bash
# 1. Download MRL Eye Dataset
kaggle datasets download -d dheerajperumandla/drowsiness-dataset -p database/datasets/raw/mrl_eye --unzip

# 2. Download Eye Gaze Dataset
kaggle datasets download -d inayat19/eye-gaze-dataset -p database/datasets/raw/eye_direction --unzip
```

---

## 3. Dataset Preprocessing Pipeline

Once raw datasets are in place, extract HOG + EAR features and create train/validation/test splits:

```bash
python vision/scripts/prepare_dataset.py
```

This outputs:
- `database/datasets/processed/features/X_features.npy`
- `database/datasets/processed/features/y_labels.npy`
- Train, validation, and test splits saved in `database/datasets/processed/`
