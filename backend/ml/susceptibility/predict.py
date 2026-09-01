"""Susceptibility-model prediction service — Phase 20.

Deliberately separate from the retired `ml/predict.py`: a distinct
`is_susceptibility_model_available()` (never the old
`is_model_available()`) and a distinct `prediction_source` value
("susceptibility_ml") wherever this is surfaced, so it can never be
confused with the retired demo model's meaning. Unlike the retired
module's `_features_to_row()`, this never calls `float(None)` — a feature
vector with any missing critical field is reported unavailable rather than
crashing or guessing.
"""
from pathlib import Path
from typing import Optional

import joblib

from ml.susceptibility.preprocessing import LANDCOVER_CATEGORIES, NUMERIC_FEATURE_NAMES, aspect_to_sin_cos

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "susceptibility_model.joblib"

_model = None
_load_attempted = False


def _load_model():
    global _model, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True
    if not MODEL_PATH.exists():
        return
    try:
        _model = joblib.load(MODEL_PATH)
    except Exception:
        _model = None


def is_susceptibility_model_available() -> bool:
    _load_model()
    return _model is not None


def _feature_vector_from_dict(features: dict) -> Optional[list]:
    """Builds a row matching ml.susceptibility.preprocessing.FEATURE_NAMES
    from a Phase 14 build_feature_vector() dict. Returns None (never a
    fabricated value) if any required numeric feature is missing."""
    values = []
    for name in NUMERIC_FEATURE_NAMES:
        value = features.get(name)
        if value is None:
            return None
        values.append(float(value))
    values.extend(aspect_to_sin_cos(features.get("aspect_degrees")))
    category = features.get("landcover_category") or "unknown"
    values.extend([1.0 if category == cat else 0.0 for cat in LANDCOVER_CATEGORIES])
    return values


def predict_susceptibility(features: dict) -> Optional[dict]:
    """Returns None if the model is unavailable OR the feature vector has a
    missing critical field — never a guessed prediction. Otherwise a dict
    with susceptibility_score (0-100), probability, and model_available."""
    _load_model()
    if _model is None:
        return None

    row = _feature_vector_from_dict(features)
    if row is None:
        return None

    proba = _model.predict_proba([row])[0]
    positive_index = list(_model.classes_).index(1)
    probability = float(proba[positive_index])

    return {
        "susceptibility_score": round(probability * 100, 2),
        "probability": round(probability, 4),
        "model_available": True,
    }


def get_feature_importance():
    """Global RandomForest feature_importances_ — NOT specific to any single
    prediction. Returns None if no model is loaded."""
    _load_model()
    if _model is None:
        return None
    from ml.susceptibility.preprocessing import FEATURE_NAMES

    return {name: round(float(importance), 4) for name, importance in zip(FEATURE_NAMES, _model.feature_importances_)}
