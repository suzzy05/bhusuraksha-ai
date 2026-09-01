"""Pseudo-absence (negative) sample generation for landslide susceptibility
modeling — Phase 20.

Real landslide inventories are presence-only: they record where a slide DID
happen, never where one didn't. Susceptibility modeling — a standard,
published GIS/remote-sensing methodology, not something invented here —
needs negative examples too. This module generates them: real coordinates
inside a real study-area bounding box, buffered away from every known real
event, kept only where the real DEM/land-cover rasters actually have
coverage, optionally restricted to a real boundary polygon, and stratified
so their slope/land-cover distribution matches the study area's own overall
distribution (computed from the same real rasters) — never a uniform random
guess that could let a model trivially separate classes on terrain alone.

Every negative sample is real coordinates + a real historical date, but a
CONSTRUCTED "no landslide recorded here" assertion — callers must tag rows
built from this module `source_type="derived"`, never `external_real`.
"""
import random
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.services.landcover_service import get_landcover
from app.services.spatial_service import nearby_events
from app.services.terrain_service import get_terrain_features
from geospatial.india.boundary import find_region_for_point

DEFAULT_BUFFER_KM = 3.0
DEFAULT_RATIO = 3
DEFAULT_MAX_ATTEMPT_MULTIPLIER = 100
SLOPE_BINS = (10.0, 20.0, 30.0, 40.0)  # yields 5 buckets: <10, 10-20, 20-30, 30-40, 40+


@dataclass
class NegativeSample:
    latitude: float
    longitude: float
    as_of: datetime
    slope_degrees: Optional[float]
    landcover_category: Optional[str]


def _slope_bin(slope_degrees: Optional[float]) -> str:
    if slope_degrees is None:
        return "unknown"
    idx = bisect_right(SLOPE_BINS, slope_degrees)
    edges = ("<10", "10-20", "20-30", "30-40", "40+")
    return edges[idx]


def compute_terrain_distribution(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float, sample_size: int = 500, random_seed: Optional[int] = None
) -> Dict[str, Dict[str, float]]:
    """Densely samples random points in the bbox and computes real
    slope-bin / land-cover-category histograms from the currently
    configured DEM/land-cover rasters. Used as the target distribution for
    stratified negative sampling. Points where a raster is unavailable are
    simply excluded from the histogram — never counted as a fabricated bin.
    Returns {} for a dimension if zero raster-covered points were sampled
    (e.g. no real DEM configured) — callers must treat that as "no target
    distribution available," not silently fall back to a fake one.
    """
    rng = random.Random(random_seed)
    slope_counts: Dict[str, int] = {}
    landcover_counts: Dict[str, int] = {}
    slope_total = 0
    landcover_total = 0

    for _ in range(sample_size):
        lat = rng.uniform(min_lat, max_lat)
        lon = rng.uniform(min_lon, max_lon)
        terrain = get_terrain_features(lat=lat, lon=lon)
        if terrain["available"] and terrain["slope_degrees"] is not None:
            key = _slope_bin(terrain["slope_degrees"])
            slope_counts[key] = slope_counts.get(key, 0) + 1
            slope_total += 1
        landcover = get_landcover(lat=lat, lon=lon)
        if landcover["available"] and landcover["normalized_category"]:
            key = landcover["normalized_category"]
            landcover_counts[key] = landcover_counts.get(key, 0) + 1
            landcover_total += 1

    return {
        "slope": {k: v / slope_total for k, v in slope_counts.items()} if slope_total else {},
        "landcover": {k: v / landcover_total for k, v in landcover_counts.items()} if landcover_total else {},
    }


def _within_buffer_of_real_event(db: Session, lat: float, lon: float, buffer_km: float) -> bool:
    pairs, _backend = nearby_events(db, lat=lat, lon=lon, radius_km=buffer_km, limit=1)
    return len(pairs) > 0


def generate_negative_samples(
    db: Session,
    *,
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    positive_dates: List[datetime],
    count: int,
    buffer_km: float = DEFAULT_BUFFER_KM,
    boundary_path: Optional[Path] = None,
    allowed_region_names: Optional[set] = None,
    target_distribution: Optional[Dict[str, Dict[str, float]]] = None,
    max_attempts: Optional[int] = None,
    random_seed: Optional[int] = None,
) -> Tuple[List[NegativeSample], dict]:
    """Generates up to `count` real-coordinate, real-dated negative samples.

    Filters applied to every candidate, in order: (1) inside the real
    boundary polygon if `boundary_path` is given — and if `allowed_region_names`
    is also given (e.g. {"Uttarakhand", "Himachal Pradesh"}), the matched
    region's name must be one of them, so a multi-state boundary file (like
    a national admin-1 file) can still restrict candidates to a specific
    pilot study area rather than the whole country, (2) at least `buffer_km`
    from every real known event, (3) DEM and land-cover both report
    `available: True` at the point (a negative gets the same real-data
    backing a positive would). Surviving candidates are then optionally
    stratified against `target_distribution` (from `compute_terrain_distribution`)
    via per-bin quotas — a bin's quota is `round(target_fraction * count)`,
    and a candidate is only accepted into a full bin's quota if room remains.

    Returns (samples, stats) where `stats` records exactly how many
    candidates were tried/rejected at each filter stage, for honest
    reporting in the caller's dataset metadata — never silently returning
    fewer than `count` without saying so.
    """
    if not positive_dates:
        raise ValueError("positive_dates must be non-empty — a negative sample's date is drawn from the real positive range.")

    rng = random.Random(random_seed)
    min_date, max_date = min(positive_dates), max(positive_dates)
    span_days = max((max_date - min_date).days, 0)

    quotas: Optional[Dict[str, Dict[str, int]]] = None
    bin_counts: Dict[str, Dict[str, int]] = {"slope": {}, "landcover": {}}
    if target_distribution:
        quotas = {
            dim: {bin_name: round(frac * count) for bin_name, frac in bins.items()}
            for dim, bins in target_distribution.items()
            if bins
        }

    max_attempts = max_attempts or count * DEFAULT_MAX_ATTEMPT_MULTIPLIER
    stats = {
        "attempts": 0,
        "rejected_outside_boundary": 0,
        "rejected_buffer": 0,
        "rejected_no_terrain": 0,
        "rejected_no_landcover": 0,
        "rejected_stratification_quota_full": 0,
        "accepted": 0,
    }

    samples: List[NegativeSample] = []
    while len(samples) < count and stats["attempts"] < max_attempts:
        stats["attempts"] += 1
        lat = rng.uniform(min_lat, max_lat)
        lon = rng.uniform(min_lon, max_lon)

        if boundary_path is not None:
            region = find_region_for_point(lat, lon, boundary_path)
            if region is None or (allowed_region_names and region not in allowed_region_names):
                stats["rejected_outside_boundary"] += 1
                continue

        if _within_buffer_of_real_event(db, lat, lon, buffer_km):
            stats["rejected_buffer"] += 1
            continue

        terrain = get_terrain_features(lat=lat, lon=lon)
        if not terrain["available"]:
            stats["rejected_no_terrain"] += 1
            continue

        landcover = get_landcover(lat=lat, lon=lon)
        if not landcover["available"]:
            stats["rejected_no_landcover"] += 1
            continue

        slope_key = _slope_bin(terrain["slope_degrees"])
        landcover_key = landcover["normalized_category"] or "unknown"

        if quotas:
            slope_quota = quotas.get("slope", {}).get(slope_key)
            if slope_quota is not None and bin_counts["slope"].get(slope_key, 0) >= slope_quota:
                stats["rejected_stratification_quota_full"] += 1
                continue
            landcover_quota = quotas.get("landcover", {}).get(landcover_key)
            if landcover_quota is not None and bin_counts["landcover"].get(landcover_key, 0) >= landcover_quota:
                stats["rejected_stratification_quota_full"] += 1
                continue

        as_of = min_date + timedelta(days=rng.randint(0, span_days)) if span_days else min_date

        samples.append(
            NegativeSample(
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                as_of=as_of,
                slope_degrees=terrain["slope_degrees"],
                landcover_category=landcover["normalized_category"],
            )
        )
        bin_counts["slope"][slope_key] = bin_counts["slope"].get(slope_key, 0) + 1
        bin_counts["landcover"][landcover_key] = bin_counts["landcover"].get(landcover_key, 0) + 1
        stats["accepted"] += 1

    stats["requested"] = count
    stats["short_by"] = count - len(samples)
    return samples, stats
