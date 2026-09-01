"""Deterministic, rule-based landslide risk scoring engine.

Phase 1 uses a weighted heuristic instead of a trained model.
`calculate_risk` is the single entry point so it can be swapped for an
ML-based implementation later without changing any callers.
"""

RAINFALL_24H_MAX = 200.0
RAINFALL_24H_WEIGHT = 22.0

RAINFALL_7D_MAX = 700.0
RAINFALL_7D_WEIGHT = 13.0

SLOPE_MAX = 60.0
SLOPE_WEIGHT = 25.0

VEGETATION_WEIGHT = 15.0

HISTORICAL_WEIGHT = 15.0

HUMIDITY_MAX = 100.0
HUMIDITY_WEIGHT = 10.0


def _clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def _rainfall_score(rainfall_24h, rainfall_7d):
    score_24h = _clamp(rainfall_24h, 0, RAINFALL_24H_MAX) / RAINFALL_24H_MAX * RAINFALL_24H_WEIGHT
    score_7d = _clamp(rainfall_7d, 0, RAINFALL_7D_MAX) / RAINFALL_7D_MAX * RAINFALL_7D_WEIGHT
    return round(score_24h + score_7d, 2)


def _slope_score(slope):
    return round(_clamp(slope, 0, SLOPE_MAX) / SLOPE_MAX * SLOPE_WEIGHT, 2)


def _vegetation_score(vegetation):
    vegetation = _clamp(vegetation, 0.0, 1.0)
    return round((1 - vegetation) * VEGETATION_WEIGHT, 2)


def _historical_score(historical_landslide):
    return HISTORICAL_WEIGHT if historical_landslide else 0.0


def _humidity_score(humidity):
    return round(_clamp(humidity, 0, HUMIDITY_MAX) / HUMIDITY_MAX * HUMIDITY_WEIGHT, 2)


def get_risk_level(risk_score):
    if risk_score <= 25:
        return "LOW"
    if risk_score <= 50:
        return "MODERATE"
    if risk_score <= 75:
        return "HIGH"
    return "CRITICAL"


def calculate_risk(
    rainfall_24h,
    rainfall_7d,
    humidity,
    temperature,
    slope,
    elevation,
    vegetation,
    historical_landslide,
):
    factors = {
        "rainfall": _rainfall_score(rainfall_24h, rainfall_7d),
        "slope": _slope_score(slope),
        "vegetation": _vegetation_score(vegetation),
        "historical": _historical_score(historical_landslide),
        "humidity": _humidity_score(humidity),
    }

    risk_score = round(min(sum(factors.values()), 100.0), 2)
    risk_level = get_risk_level(risk_score)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "factors": factors,
    }
