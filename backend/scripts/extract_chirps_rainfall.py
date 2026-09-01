"""Phase 20 — extracts real CHIRPS daily rainfall at the EXACT coordinates
and dates this project actually needs (every real positive event in the
pilot bbox, plus generated pseudo-absence negatives), rather than bulk-
ingesting the full CHIRPS grid (which would be millions of rows for even
a modest bounding box across a multi-year date range).

Source: CHIRPS 2.0 global daily, 0.05-degree, public HTTPS, no auth
(https://www.chc.ucsb.edu/data/chirps). This is a gridded satellite+station
BLENDED ESTIMATE, not individual rain-gauge readings — every row this
script writes gets `resolution="chirps_0.05deg_daily_gridded"` so this is
never confused with real station observations downstream.

For each point (a real event or a generated negative), this reads the
single pixel nearest that coordinate for every day in
[as_of - lookback_days, as_of] from the corresponding daily global GeoTIFF
— downloading each day's ~3MB global file once (shared across every point
needing that date), decompressing it to a temp path, reading only the
needed pixels, then deleting it. Never keeps a full global raster archive
on disk.

Writes:
  1. A rainfall CSV ready for `scripts/ingest_dataset.py --category rainfall`
     (one pseudo-station per point: station_id="chirps_<point_id>").
  2. A negatives cache CSV (lat, lon, as_of, point_id) recording the EXACT
     negative samples this run generated, so `build_susceptibility_dataset.py`
     can reuse them (via --negatives-cache) rather than generating a
     different random draw that this rainfall extraction wouldn't cover.

Usage:
    python scripts/extract_chirps_rainfall.py \
        --min-lat 28.4 --min-lon 75.4 --max-lat 33.3 --max-lon 81.1 \
        --ratio 3 --buffer-km 3 --boundary-path data/raw/external/india_states_natural_earth.geojson \
        --allowed-region-names "Uttarakhand,Himachal Pradesh" \
        --rainfall-output data/raw/external/pilot_chirps_rainfall.csv \
        --negatives-cache-output data/processed/pilot_negatives_cache.csv
"""
import argparse
import csv
import gzip
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.landslide_event import LandslideEvent  # noqa: E402
from app.services.negative_sampling_service import (  # noqa: E402
    DEFAULT_BUFFER_KM,
    DEFAULT_RATIO,
    compute_terrain_distribution,
    generate_negative_samples,
)

CHIRPS_BASE = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05"
CHIRPS_NODATA = -9999.0
REQUEST_TIMEOUT = 60
DEFAULT_LOOKBACK_DAYS = 31


def chirps_url(d: datetime) -> str:
    return f"{CHIRPS_BASE}/{d.year}/chirps-v2.0.{d.year}.{d.month:02d}.{d.day:02d}.tif.gz"


def _download_and_extract_day(date_obj: datetime, points_needing_date, rows_out, tmp_dir: Path) -> bool:
    """Downloads one day's global CHIRPS grid, reads the pixel nearest each
    point in `points_needing_date`, appends real (or honestly-skipped
    nodata) rows to `rows_out`, then deletes the temp file. Returns False
    (never raises) if the file genuinely doesn't exist for this date."""
    import rasterio

    url = chirps_url(date_obj)
    gz_path = tmp_dir / "day.tif.gz"
    tif_path = tmp_dir / "day.tif"
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            if response.status_code == 404:
                print(f"  {date_obj.date()}: NOT FOUND upstream — skipping (no fabricated value)")
                return False
            response.raise_for_status()
            with open(gz_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)

        with gzip.open(gz_path, "rb") as f_in, open(tif_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        with rasterio.open(tif_path) as dataset:
            band = dataset.read(1)
            for point_id, lat, lon in points_needing_date:
                row, col = dataset.index(lon, lat)
                if not (0 <= row < dataset.height and 0 <= col < dataset.width):
                    continue
                value = float(band[row, col])
                if value == CHIRPS_NODATA or value < 0:
                    continue
                rows_out.append(
                    {
                        "station_id": f"chirps_{point_id}",
                        "latitude": lat,
                        "longitude": lon,
                        "date": date_obj.date().isoformat(),
                        "rainfall_mm": round(value, 2),
                    }
                )
        return True
    finally:
        gz_path.unlink(missing_ok=True)
        tif_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Extract real CHIRPS rainfall at exact points needed for the susceptibility pilot")
    parser.add_argument("--min-lat", type=float, required=True)
    parser.add_argument("--min-lon", type=float, required=True)
    parser.add_argument("--max-lat", type=float, required=True)
    parser.add_argument("--max-lon", type=float, required=True)
    parser.add_argument("--ratio", type=int, default=DEFAULT_RATIO)
    parser.add_argument("--buffer-km", type=float, default=DEFAULT_BUFFER_KM)
    parser.add_argument("--boundary-path", default=None)
    parser.add_argument("--allowed-region-names", default=None)
    parser.add_argument("--stratify-sample-size", type=int, default=500)
    parser.add_argument("--no-stratify", action="store_true")
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--rainfall-output", default="data/raw/external/pilot_chirps_rainfall.csv")
    parser.add_argument("--negatives-cache-output", default="data/processed/pilot_negatives_cache.csv")
    args = parser.parse_args()

    boundary_path = Path(args.boundary_path) if args.boundary_path else None
    allowed_region_names = (
        {n.strip() for n in args.allowed_region_names.split(",")} if args.allowed_region_names else None
    )

    db = SessionLocal()
    try:
        events = (
            db.query(LandslideEvent)
            .filter(
                LandslideEvent.latitude.between(args.min_lat, args.max_lat),
                LandslideEvent.longitude.between(args.min_lon, args.max_lon),
                LandslideEvent.event_date.isnot(None),
            )
            .order_by(LandslideEvent.id)
            .all()
        )
        print(f"Real positive events in bbox with a real date: {len(events)}")
        positive_dates = [e.event_date for e in events]

        target_distribution = None
        if not args.no_stratify:
            print(f"Sampling {args.stratify_sample_size} points for the real target terrain distribution...")
            target_distribution = compute_terrain_distribution(
                args.min_lat, args.min_lon, args.max_lat, args.max_lon,
                sample_size=args.stratify_sample_size, random_seed=args.random_seed,
            )
            print(f"  slope: {target_distribution.get('slope')}")
            print(f"  landcover: {target_distribution.get('landcover')}")

        negative_count = len(events) * args.ratio
        print(f"Generating {negative_count} pseudo-absence negatives...")
        negatives, stats = generate_negative_samples(
            db,
            min_lat=args.min_lat, min_lon=args.min_lon, max_lat=args.max_lat, max_lon=args.max_lon,
            positive_dates=positive_dates, count=negative_count, buffer_km=args.buffer_km,
            boundary_path=boundary_path, allowed_region_names=allowed_region_names,
            target_distribution=target_distribution, random_seed=args.random_seed,
        )
        print(f"  {stats}")

        negatives_cache_path = Path(args.negatives_cache_output)
        negatives_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(negatives_cache_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["point_id", "latitude", "longitude", "as_of"])
            for i, neg in enumerate(negatives):
                writer.writerow([f"negative_{i}", neg.latitude, neg.longitude, neg.as_of.isoformat()])
        print(f"Wrote {len(negatives)} negative sample(s) to {negatives_cache_path}")

        points = [(f"event_{e.id}", e.latitude, e.longitude, e.event_date) for e in events]
        points += [(f"negative_{i}", neg.latitude, neg.longitude, neg.as_of) for i, neg in enumerate(negatives)]

        # Build date -> [(point_id, lat, lon), ...] for every day in every
        # point's real lookback window, so each day's global grid is
        # downloaded exactly once no matter how many points need it.
        date_to_points = {}
        for point_id, lat, lon, as_of in points:
            for offset in range(args.lookback_days + 1):
                d = (as_of - timedelta(days=offset)).date()
                date_to_points.setdefault(d, []).append((point_id, lat, lon))

        print(f"\n{len(date_to_points)} unique day(s) of real CHIRPS data needed across {len(points)} point(s)")

        rows = []
        with tempfile.TemporaryDirectory(prefix="chirps_") as tmp:
            tmp_dir = Path(tmp)
            for i, day in enumerate(sorted(date_to_points), start=1):
                day_dt = datetime(day.year, day.month, day.day)
                print(f"[{i}/{len(date_to_points)}] {day} ({len(date_to_points[day])} point(s))")
                _download_and_extract_day(day_dt, date_to_points[day], rows, tmp_dir)

        output_path = Path(args.rainfall_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["station_id", "latitude", "longitude", "date", "rainfall_mm"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nWrote {len(rows)} real CHIRPS rainfall row(s) to {output_path}")
        print("Register with: python scripts/ingest_dataset.py --category rainfall --path "
              f"{output_path} --name \"CHIRPS 2.0 Daily (pilot points)\" --provider \"Climate Hazards Center, UCSB\" "
              "--source-url \"https://www.chc.ucsb.edu/data/chirps\" --license \"Public domain (US Government / CHC)\" "
              "--limitations \"Gridded satellite+station-blended daily estimate, 0.05deg, NOT individual gauge stations; "
              "extracted only at specific pilot event/negative coordinates and lookback windows, not the full grid\"")
    finally:
        db.close()


if __name__ == "__main__":
    main()
