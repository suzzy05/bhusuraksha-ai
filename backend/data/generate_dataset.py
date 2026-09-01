"""Generates a small, reproducible SYNTHETIC/DEMO training dataset for the
Phase 2 landslide risk classifier.

IMPORTANT: This is NOT a real-world landslide dataset. It is a hand-crafted,
seeded approximation created only to exercise the ML pipeline end-to-end for
this prototype. A later phase is expected to replace it with a real
environmental/landslide dataset.

Run directly to (re)generate backend/data/raw/landslide_training_data.csv:

    python data/generate_dataset.py
"""
import csv
from pathlib import Path

import numpy as np

RANDOM_SEED = 42
SAMPLES_PER_CLASS = 150

OUTPUT_PATH = Path(__file__).resolve().parent / "raw" / "demo" / "landslide_training_data.csv"

FIELDNAMES = [
    "rainfall_24h",
    "rainfall_7d",
    "humidity",
    "temperature",
    "slope",
    "elevation",
    "vegetation",
    "historical_landslide",
    "risk_level",
]

# Per-class (min, max) uniform ranges used to synthesize plausible feature
# values, plus the probability of a historical landslide for that class.
CLASS_PROFILES = {
    "LOW": {
        "rainfall_24h": (0, 40),
        "rainfall_7d": (0, 150),
        "humidity": (30, 60),
        "temperature": (18, 35),
        "slope": (0, 15),
        "elevation": (0, 1800),
        "vegetation": (0.6, 1.0),
        "historical_landslide_prob": 0.05,
    },
    "MODERATE": {
        "rainfall_24h": (30, 80),
        "rainfall_7d": (120, 300),
        "humidity": (50, 75),
        "temperature": (15, 30),
        "slope": (10, 25),
        "elevation": (100, 2000),
        "vegetation": (0.4, 0.7),
        "historical_landslide_prob": 0.20,
    },
    "HIGH": {
        "rainfall_24h": (70, 140),
        "rainfall_7d": (250, 500),
        "humidity": (65, 88),
        "temperature": (12, 26),
        "slope": (20, 40),
        "elevation": (200, 2200),
        "vegetation": (0.2, 0.5),
        "historical_landslide_prob": 0.45,
    },
    "CRITICAL": {
        "rainfall_24h": (120, 200),
        "rainfall_7d": (450, 700),
        "humidity": (80, 100),
        "temperature": (8, 22),
        "slope": (35, 60),
        "elevation": (300, 2500),
        "vegetation": (0.05, 0.3),
        "historical_landslide_prob": 0.75,
    },
}


def generate_rows():
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    for risk_level, profile in CLASS_PROFILES.items():
        for _ in range(SAMPLES_PER_CLASS):
            rows.append(
                {
                    "rainfall_24h": round(float(rng.uniform(*profile["rainfall_24h"])), 1),
                    "rainfall_7d": round(float(rng.uniform(*profile["rainfall_7d"])), 1),
                    "humidity": round(float(rng.uniform(*profile["humidity"])), 1),
                    "temperature": round(float(rng.uniform(*profile["temperature"])), 1),
                    "slope": round(float(rng.uniform(*profile["slope"])), 1),
                    "elevation": round(float(rng.uniform(*profile["elevation"])), 1),
                    "vegetation": round(float(rng.uniform(*profile["vegetation"])), 2),
                    "historical_landslide": bool(rng.random() < profile["historical_landslide_prob"]),
                    "risk_level": risk_level,
                }
            )

    order = rng.permutation(len(rows))
    return [rows[i] for i in order]


def generate_dataset():
    rows = generate_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic DEMO rows to {OUTPUT_PATH}")
    return rows


if __name__ == "__main__":
    generate_dataset()
