"""Feature/target schema for the Phase 20 susceptibility model — aligned to
`app.services.feature_engineering_service.build_feature_vector()`'s real
output, deliberately NOT the retired demo model's `ml/preprocessing.py`
feature list (which had no real-data equivalent for several of its fields
and used `humidity`/`temperature`/`vegetation` this project never actually
measures).

Kept in its own package so it can never be confused with, or accidentally
reuse artifacts from, the retired Phase 2 demo model.
"""
import csv
from datetime import datetime
from math import cos, radians, sin
from typing import List, Optional, Tuple

LANDCOVER_CATEGORIES = ("forest", "grassland", "cropland", "urban", "bare_land", "water", "unknown")

# aspect_degrees is deliberately NOT in here: it's a compass direction
# (0-360, circular — 359 deg is next to 0 deg, not far from it) and it is
# legitimately None on flat ground (terrain_service reports "undefined",
# never fabricating a direction), which every other feature here treats as
# a row to drop. Dropping every flat-terrain row would be wrong — flat
# ground is a real, common, and informative class for susceptibility.
# Instead it gets its own sin/cos encoding below (aspect_sin, aspect_cos),
# with the origin (0, 0) — off the unit circle every real direction maps
# to — used for the undefined case, never a guessed compass direction.
NUMERIC_FEATURE_NAMES = [
    "rainfall_24h",
    "rainfall_72h",
    "rainfall_7d",
    "rainfall_30d",
    "antecedent_rainfall_index",
    "elevation_m",
    "slope_degrees",
    "historical_landslide_density_per_km2",
]

ASPECT_FEATURE_NAMES = ["aspect_sin", "aspect_cos"]

# One-hot columns for landcover_category, appended after the numeric features.
FEATURE_NAMES = NUMERIC_FEATURE_NAMES + ASPECT_FEATURE_NAMES + [f"landcover_{cat}" for cat in LANDCOVER_CATEGORIES]


def aspect_to_sin_cos(aspect_degrees: Optional[float]) -> List[float]:
    if aspect_degrees is None:
        return [0.0, 0.0]
    rad = radians(float(aspect_degrees))
    return [round(sin(rad), 6), round(cos(rad), 6)]

TARGET_NAME = "label"


def _one_hot_landcover(category: str) -> List[float]:
    return [1.0 if category == cat else 0.0 for cat in LANDCOVER_CATEGORIES]


def row_to_feature_vector(row: dict, *, exclude_density: bool = False) -> List[float]:
    """Converts one CSV row-dict (from build_susceptibility_dataset.py) into
    a feature vector matching FEATURE_NAMES. Never guesses a missing numeric
    value — the caller is expected to have already dropped rows with any
    missing critical feature; this raises if that invariant was violated."""
    values = []
    for name in NUMERIC_FEATURE_NAMES:
        if exclude_density and name == "historical_landslide_density_per_km2":
            continue
        raw = row.get(name)
        if raw is None or raw == "":
            raise ValueError(f"Row is missing required feature '{name}' — dataset builder should have dropped this row.")
        values.append(float(raw))
    raw_aspect = row.get("aspect_degrees")
    values.extend(aspect_to_sin_cos(float(raw_aspect) if raw_aspect not in (None, "") else None))
    values.extend(_one_hot_landcover(row.get("landcover_category") or "unknown"))
    return values


def load_dataset(path: str, *, exclude_density: bool = False) -> Tuple[List[List[float]], List[int], List[datetime]]:
    """Loads a Phase 20 susceptibility CSV. Returns (X, y, as_of_dates) —
    dates are returned alongside X/y so callers can do a real time-based
    split (never a random one) rather than needing to re-read the file."""
    X, y, dates = [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            X.append(row_to_feature_vector(row, exclude_density=exclude_density))
            y.append(int(row["label"]))
            dates.append(datetime.fromisoformat(row["as_of"]))
    return X, y, dates


def time_based_split(X, y, dates, test_fraction: float = 0.2):
    """Sorts by real date ascending and splits chronologically — train on
    the earliest rows, test on the most recent — per Phase 15's explicit
    requirement that real training never use a random split (which would
    let the model 'see the future' relative to some test rows)."""
    order = sorted(range(len(dates)), key=lambda i: dates[i])
    split_at = int(len(order) * (1 - test_fraction))
    train_idx, test_idx = order[:split_at], order[split_at:]
    X_train = [X[i] for i in train_idx]
    y_train = [y[i] for i in train_idx]
    X_test = [X[i] for i in test_idx]
    y_test = [y[i] for i in test_idx]
    split_date = dates[order[split_at]] if test_idx else None
    return X_train, X_test, y_train, y_test, split_date
