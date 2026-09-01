"""Loads the raw CSV dataset and turns it into numeric feature/label arrays
for training. Kept dependency-free (stdlib `csv` only, no pandas) so Phase 2
does not need to add a new dependency beyond scikit-learn/joblib.
"""
import csv
from pathlib import Path

from sklearn.model_selection import train_test_split

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "demo" / "landslide_training_data.csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed" / "landslide_training_data_processed.csv"

FEATURE_NAMES = [
    "rainfall_24h",
    "rainfall_7d",
    "humidity",
    "temperature",
    "slope",
    "elevation",
    "vegetation",
    "historical_landslide",
]
TARGET_NAME = "risk_level"


def load_raw_rows(path=RAW_DATA_PATH):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _to_bool_flag(value):
    return 1.0 if str(value).strip().lower() in ("true", "1") else 0.0


def rows_to_features(rows):
    X, y = [], []
    for row in rows:
        X.append(
            [
                float(row["rainfall_24h"]),
                float(row["rainfall_7d"]),
                float(row["humidity"]),
                float(row["temperature"]),
                float(row["slope"]),
                float(row["elevation"]),
                float(row["vegetation"]),
                _to_bool_flag(row["historical_landslide"]),
            ]
        )
        y.append(row[TARGET_NAME])
    return X, y


def save_processed_dataset(rows):
    """Writes the numerically-encoded dataset for traceability/inspection."""
    PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_DATA_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_NAMES + [TARGET_NAME])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **{name: row[name] for name in FEATURE_NAMES if name != "historical_landslide"},
                    "historical_landslide": _to_bool_flag(row["historical_landslide"]),
                    TARGET_NAME: row[TARGET_NAME],
                }
            )


def load_dataset(path=RAW_DATA_PATH):
    rows = load_raw_rows(path)
    save_processed_dataset(rows)
    return rows_to_features(rows)


def split_dataset(X, y, test_size=0.2, random_state=42):
    return train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)
