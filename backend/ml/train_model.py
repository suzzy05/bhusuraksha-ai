"""Trains the Phase 2 landslide risk RandomForestClassifier on the demo
synthetic dataset and saves the artifacts consumed by `ml/predict.py`.

Usage (from the `backend/` directory):

    python -m ml.train_model
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier

from ml.evaluate import evaluate_model, print_training_summary
from ml.preprocessing import FEATURE_NAMES, load_dataset, split_dataset

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "landslide_model.joblib"
METADATA_PATH = ARTIFACTS_DIR / "model_metadata.json"


def train():
    X, y = load_dataset()
    X_train, X_test, y_train, y_test = split_dataset(X, y)

    model = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)
    model.fit(X_train, y_train)

    metrics = evaluate_model(model, X_test, y_test)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    metadata = {
        "feature_names": FEATURE_NAMES,
        "model_type": "RandomForestClassifier",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": len(X),
        "training_rows": len(X_train),
        "testing_rows": len(X_test),
        "metrics": metrics,
        "notes": "Trained on synthetic/demo data — see backend/data/raw/README.md.",
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print_training_summary(len(X), len(X_train), len(X_test), metrics)


if __name__ == "__main__":
    train()
