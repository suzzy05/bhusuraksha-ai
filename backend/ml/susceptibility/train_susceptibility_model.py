"""Trains the Phase 20 landslide SUSCEPTIBILITY model on a real
presence/pseudo-absence dataset produced by
`scripts/build_susceptibility_dataset.py`.

This predicts relative spatial susceptibility (a standard, published GIS
methodology), never a validated forecast of a future event — see
`docs/ML_LIMITATIONS.md`. Kept fully separate from the retired Phase 2 demo
model: different package, different artifacts directory, different
`prediction_source` value when served.

Usage (from the `backend/` directory):

    python -m ml.susceptibility.train_susceptibility_model --dataset data/processed/susceptibility_dataset.csv
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier

from ml.susceptibility.evaluate import evaluate_binary_model, print_training_summary
from ml.susceptibility.preprocessing import FEATURE_NAMES, load_dataset, time_based_split

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "susceptibility_model.joblib"
METADATA_PATH = ARTIFACTS_DIR / "susceptibility_model_metadata.json"


def _train_one(X, y, dates, test_fraction, exclude_density, random_state=42):
    X_train, X_test, y_train, y_test, split_date = time_based_split(X, y, dates, test_fraction=test_fraction)
    model = RandomForestClassifier(n_estimators=200, max_depth=8, class_weight="balanced", random_state=random_state)
    model.fit(X_train, y_train)
    metrics = evaluate_binary_model(model, X_test, y_test)
    return model, metrics, len(X_train), len(X_test), split_date


def train(dataset_path: str, test_fraction: float = 0.2):
    X, y, dates = load_dataset(dataset_path)
    if len(set(y)) < 2:
        raise ValueError("Dataset must contain both positive and negative rows to train a classifier.")

    model, metrics, n_train, n_test, split_date = _train_one(X, y, dates, test_fraction, exclude_density=False)
    print_training_summary(len(X), n_train, n_test, split_date, metrics)

    # Ablation: same split, same hyperparameters, density feature removed —
    # reported alongside the real result rather than hidden, per the plan's
    # requirement to surface whether the model is mostly just relearning
    # "near known events."
    X_no_density, _, dates_no_density = load_dataset(dataset_path, exclude_density=True)
    model_ablation, metrics_ablation, _, _, _ = _train_one(X_no_density, y, dates_no_density, test_fraction, exclude_density=True)
    print("\nAblation (historical_landslide_density_per_km2 excluded):")
    print(f"  PR-AUC: {metrics_ablation['pr_auc']}  ROC-AUC: {metrics_ablation['roc_auc']}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    metadata = {
        "model_type": "RandomForestClassifier",
        "target": "susceptibility (positive-class probability of a real vs. pseudo-absence landslide record)",
        "feature_names": FEATURE_NAMES,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path),
        "dataset_rows": len(X),
        "training_rows": n_train,
        "testing_rows": n_test,
        "split_type": "time_based",
        "split_date": split_date.isoformat() if split_date else None,
        "metrics": metrics,
        "ablation_without_historical_density": metrics_ablation,
        "notes": (
            "Susceptibility score, NOT a validated forecast. Trained on a real "
            "presence/pseudo-absence dataset (see the dataset's own .metadata.json for "
            "negative-sampling methodology). See docs/ML_LIMITATIONS.md for full context."
        ),
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved metadata to {METADATA_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the Phase 20 susceptibility model")
    parser.add_argument("--dataset", required=True, help="Path to a CSV from scripts/build_susceptibility_dataset.py")
    parser.add_argument("--test-fraction", type=float, default=0.2)
    args = parser.parse_args()
    train(args.dataset, test_fraction=args.test_fraction)
