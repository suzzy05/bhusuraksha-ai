"""ML prediction service for landslide risk.

Loads the trained RandomForestClassifier (if present) once, lazily, and
exposes a small API the FastAPI route uses. If the model artifact is
missing or fails to load, `is_model_available()` returns False and callers
are expected to fall back to the deterministic rule-based engine in
`app/services/risk_service.py` — this module never raises for a missing
model.
"""
from pathlib import Path

import joblib

from ml.preprocessing import FEATURE_NAMES

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "landslide_model.joblib"

# Maps each risk class to a representative score used to convert class
# probabilities into a single 0-100 risk_score:
#
#   risk_score = sum(probability_of_class * class_score for each class)
#
# e.g. probabilities {HIGH: 0.70, CRITICAL: 0.20, MODERATE: 0.08, LOW: 0.02}
#   -> 0.70*62.5 + 0.20*87.5 + 0.08*37.5 + 0.02*12.5 = 63.5
# This keeps the score continuous and sensitive to *how confidently* the
# model leans toward a class, rather than collapsing to a fixed step value.
RISK_LEVEL_SCORES = {"LOW": 12.5, "MODERATE": 37.5, "HIGH": 62.5, "CRITICAL": 87.5}

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


def is_model_available() -> bool:
    _load_model()
    return _model is not None


def _features_to_row(features: dict):
    return [[
        float(features["rainfall_24h"]),
        float(features["rainfall_7d"]),
        float(features["humidity"]),
        float(features["temperature"]),
        float(features["slope"]),
        float(features["elevation"]),
        float(features["vegetation"]),
        1.0 if features["historical_landslide"] else 0.0,
    ]]


def _risk_score_from_probabilities(probabilities: dict) -> float:
    score = sum(probabilities.get(level, 0.0) * class_score for level, class_score in RISK_LEVEL_SCORES.items())
    return round(max(0.0, min(100.0, score)), 2)


def predict_risk_ml(features: dict):
    """Returns None if the model is unavailable, otherwise a dict with
    predicted_risk_level, probabilities, risk_score, and model_available."""
    _load_model()
    if _model is None:
        return None

    row = _features_to_row(features)
    predicted_class = _model.predict(row)[0]
    proba = _model.predict_proba(row)[0]

    probabilities = {level: 0.0 for level in RISK_LEVEL_SCORES}
    for cls, p in zip(_model.classes_, proba):
        probabilities[cls] = round(float(p), 4)

    return {
        "predicted_risk_level": predicted_class,
        "probabilities": probabilities,
        "risk_score": _risk_score_from_probabilities(probabilities),
        "model_available": True,
    }


def get_feature_importance():
    """Global RandomForest feature_importances_ — NOT specific to any single
    prediction. Returns None if no model is loaded."""
    _load_model()
    if _model is None:
        return None
    return {
        name: round(float(importance), 4)
        for name, importance in zip(FEATURE_NAMES, _model.feature_importances_)
    }
