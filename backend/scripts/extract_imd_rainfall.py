"""Phase 20 — extracts real IMD (India Meteorological Department) gridded
daily rainfall at the EXACT coordinates and dates needed (every real
positive event in the pilot bbox, plus generated pseudo-absence
negatives), rather than bulk-ingesting the full 124-year national grid.

Source: IMD's own public "New High Spatial Resolution (0.25x0.25 degree)
Long Period (1901-2024) Daily Gridded Rainfall Data Set Over India"
(https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html) — a public
web form (POST year -> NetCDF file), no login/API key/payment. This is
India's own official meteorological rainfall product, preferred here over
a global gridded estimate (CHIRPS, see extract_chirps_rainfall.py) because
it's the authoritative national dataset for exactly the area this pilot
covers. Every row this script writes gets
`resolution="imd_0.25deg_daily_gridded"` so it is never confused with
individual rain-gauge station observations downstream.

For each point (a real event or a generated negative), this downloads
(and caches) the ONE yearly NetCDF file covering that point's
[as_of - lookback_days, as_of] window (crossing a year boundary pulls in
both years' files), reads the real pixel value nearest that coordinate for
each needed day via the file's own TIME dimension (never assumes band
index == day-of-year, since IMD's grid explicitly encodes real calendar
dates per band), and writes one row per (point, date, real value).
`-999`/fill values are skipped, never fabricated as 0.

Writes the same two outputs as extract_chirps_rainfall.py (a rainfall CSV
for scripts/ingest_dataset.py --category rainfall, and a negatives-cache
CSV for scripts/build_susceptibility_dataset.py --negatives-cache), so
either rainfall source plugs into the same downstream pipeline.

Usage:
    python scripts/extract_imd_rainfall.py \
        --min-lat 28.4 --min-lon 75.4 --max-lat 33.3 --max-lon 81.1 \
        --ratio 3 --buffer-km 3 --boundary-path data/raw/external/india_states_natural_earth.geojson \
        --allowed-region-names "Uttarakhand,Himachal Pradesh" \
        --rainfall-output data/raw/external/pilot_imd_rainfall.csv \
        --negatives-cache-output data/processed/pilot_negatives_cache.csv
"""
import argparse
import csv
import sys
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

IMD_FORM_URL = "https://imdpune.gov.in/cmpg/Griddata/RF25.php"
IMD_FIELD_NAME = "RF25"
IMD_FILL_VALUE = -999.0
REQUEST_TIMEOUT = 180
DEFAULT_LOOKBACK_DAYS = 31
TIME_EPOCH = datetime(1900, 12, 31)


def _year_cache_path(cache_dir: Path, year: int) -> Path:
    return cache_dir / f"ind{year}_rfp25.nc"


def download_year(year: int, cache_dir: Path) -> Path:
    """Downloads (or reuses a cached) IMD gridded-rainfall NetCDF for one
    calendar year via the public RF25.php form. Never raises for a year
    IMD simply doesn't have — the caller treats a missing file as
    'no real data for this year', not a crash."""
    dest = _year_cache_path(cache_dir, year)
    if dest.exists():
        print(f"  already have {dest.name}, skipping")
        return dest

    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_suffix(".part")
    response = requests.post(IMD_FORM_URL, data={IMD_FIELD_NAME: str(year)}, timeout=REQUEST_TIMEOUT, stream=True)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "octet-stream" not in content_type and "netcdf" not in content_type.lower():
        raise RuntimeError(f"Unexpected response for year {year} (Content-Type: {content_type}) — IMD's form may have changed.")

    with open(tmp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    tmp_path.rename(dest)
    print(f"  downloaded {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
    return dest


def _band_date_map(dataset) -> dict:
    """Real calendar date -> 1-based band index, parsed from the file's own
    NETCDF_DIM_TIME_VALUES tag (days since 1900-12-31) — never assumed
    from band position, since that's exactly the kind of guess this
    project's conventions forbid."""
    raw = dataset.tags()["NETCDF_DIM_TIME_VALUES"].strip("{}")
    offsets = [int(v) for v in raw.split(",")]
    return {(TIME_EPOCH + timedelta(days=offset)).date(): i + 1 for i, offset in enumerate(offsets)}


def extract_points_for_year(year: int, points_needing_year, cache_dir: Path, rows_out: list):
    import rasterio

    nc_path = download_year(year, cache_dir)
    subdataset = f'NETCDF:"{nc_path}":RAINFALL'
    with rasterio.open(subdataset) as dataset:
        date_to_band = _band_date_map(dataset)
        band_cache = {}
        for point_id, lat, lon, needed_date in points_needing_year:
            band_idx = date_to_band.get(needed_date)
            if band_idx is None:
                continue  # real gap in IMD's own calendar (e.g. an incomplete year) — honestly skipped
            if band_idx not in band_cache:
                band_cache[band_idx] = dataset.read(band_idx)
            band = band_cache[band_idx]
            row, col = dataset.index(lon, lat)
            if not (0 <= row < dataset.height and 0 <= col < dataset.width):
                continue
            value = float(band[row, col])
            if value == IMD_FILL_VALUE or value < 0:
                continue
            rows_out.append(
                {
                    "station_id": f"imd_{point_id}",
                    "latitude": lat,
                    "longitude": lon,
                    "date": needed_date.isoformat(),
                    "rainfall_mm": round(value, 2),
                }
            )


def main():
    parser = argparse.ArgumentParser(description="Extract real IMD gridded rainfall at exact points needed for the susceptibility pilot")
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
    parser.add_argument("--nc-cache-dir", default="data/raw/external/imd_rainfall")
    parser.add_argument("--rainfall-output", default="data/raw/external/pilot_imd_rainfall.csv")
    parser.add_argument("--negatives-cache-output", default="data/processed/pilot_negatives_cache.csv")
    parser.add_argument("--reuse-negatives-cache", action="store_true", help="Reuse an existing negatives cache instead of generating a new one")
    args = parser.parse_args()

    boundary_path = Path(args.boundary_path) if args.boundary_path else None
    allowed_region_names = (
        {n.strip() for n in args.allowed_region_names.split(",")} if args.allowed_region_names else None
    )
    negatives_cache_path = Path(args.negatives_cache_output)

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

        if args.reuse_negatives_cache and negatives_cache_path.exists():
            print(f"Reusing existing negatives cache: {negatives_cache_path}")
            negatives = []
            with open(negatives_cache_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    negatives.append((row["point_id"], float(row["latitude"]), float(row["longitude"]), datetime.fromisoformat(row["as_of"])))
        else:
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
            generated, stats = generate_negative_samples(
                db,
                min_lat=args.min_lat, min_lon=args.min_lon, max_lat=args.max_lat, max_lon=args.max_lon,
                positive_dates=positive_dates, count=negative_count, buffer_km=args.buffer_km,
                boundary_path=boundary_path, allowed_region_names=allowed_region_names,
                target_distribution=target_distribution, random_seed=args.random_seed,
            )
            print(f"  {stats}")
            negatives = [(f"negative_{i}", n.latitude, n.longitude, n.as_of) for i, n in enumerate(generated)]

            negatives_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(negatives_cache_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["point_id", "latitude", "longitude", "as_of"])
                for point_id, lat, lon, as_of in negatives:
                    writer.writerow([point_id, lat, lon, as_of.isoformat()])
            print(f"Wrote {len(negatives)} negative sample(s) to {negatives_cache_path}")

        points = [(f"event_{e.id}", e.latitude, e.longitude, e.event_date) for e in events]
        points += negatives

        # Build year -> [(point_id, lat, lon, real_date), ...] for every real
        # calendar day in every point's lookback window, so each year's file
        # is downloaded exactly once no matter how many points/days need it.
        year_to_points = {}
        for point_id, lat, lon, as_of in points:
            for offset in range(args.lookback_days + 1):
                d = (as_of - timedelta(days=offset)).date()
                year_to_points.setdefault(d.year, []).append((point_id, lat, lon, d))

        print(f"\n{len(year_to_points)} year(s) of real IMD data needed across {len(points)} point(s): {sorted(year_to_points)}")

        rows = []
        cache_dir = Path(args.nc_cache_dir)
        for i, year in enumerate(sorted(year_to_points), start=1):
            print(f"[{i}/{len(year_to_points)}] year {year} ({len(year_to_points[year])} point-day pair(s))")
            try:
                extract_points_for_year(year, year_to_points[year], cache_dir, rows)
            except Exception as exc:  # noqa: BLE001 - one bad year must not abort the whole run
                print(f"  FAILED for year {year}: {exc}")

        output_path = Path(args.rainfall_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["station_id", "latitude", "longitude", "date", "rainfall_mm"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nWrote {len(rows)} real IMD rainfall row(s) to {output_path}")
        print("Register with: python scripts/ingest_dataset.py --category rainfall --path "
              f"{output_path} --name \"IMD Gridded Rainfall 0.25deg (pilot points)\" "
              "--provider \"India Meteorological Department\" "
              "--source-url \"https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html\" "
              "--license \"Public (IMD data-access disclaimer applies; no accuracy warranty)\" "
              "--limitations \"Gridded (0.25deg) daily rainfall estimate interpolated from IMD's station "
              "network, not individual gauge readings; extracted only at specific pilot event/negative "
              "coordinates and lookback windows, not the full national grid\""
              )
    finally:
        db.close()


if __name__ == "__main__":
    main()
