"""Phase 20 — downloads and mosaics real, open, public DEM and land-cover
rasters covering a bounding box, so they can be pointed at via
BHUSURAKSHA_DEM_DATA_PATH / BHUSURAKSHA_LANDCOVER_PATH. One-time data-prep
tooling, not application runtime code.

Real sources (no auth, no API key):
- DEM: Copernicus DEM GLO-30, AWS Open Data Registry
  (https://registry.opendata.aws/copernicus-dem/), 1x1 degree COG tiles.
- Land cover: ESA WorldCover 10m 2021 v200, AWS Open Data Registry
  (https://registry.opendata.aws/esa-worldcover/), 3x3 degree tiles — the
  exact product this project's ESA_WORLDCOVER legend
  (geospatial/landcover_schemes.py) already maps.

Never bakes a real dataset into the repo — downloads go to --raw-dir
(default data/raw/external/, already gitignored) and the mosaicked output
is a single new GeoTIFF you then register via scripts/ingest_dataset.py
--category terrain/vegetation and configure via the env vars above.

Usage:
    python scripts/prepare_pilot_rasters.py \
        --min-lat 28 --min-lon 75 --max-lat 34 --max-lon 82 \
        --raw-dir data/raw/external/pilot_rasters
"""
import argparse
import math
import sys
from pathlib import Path

import requests

DEM_BASE = "https://copernicus-dem-30m.s3.amazonaws.com"
WORLDCOVER_BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"
CHUNK_SIZE = 1024 * 1024
REQUEST_TIMEOUT = 60


def _ns_ew(lat_tile: int, lon_tile: int):
    ns = "N" if lat_tile >= 0 else "S"
    ew = "E" if lon_tile >= 0 else "W"
    return ns, abs(lat_tile), ew, abs(lon_tile)


def dem_tile_ids(min_lat, min_lon, max_lat, max_lon):
    for lat in range(math.floor(min_lat), math.floor(max_lat) + 1):
        for lon in range(math.floor(min_lon), math.floor(max_lon) + 1):
            yield lat, lon


def worldcover_tile_ids(min_lat, min_lon, max_lat, max_lon):
    def floor3(x):
        return int(math.floor(x / 3.0) * 3)

    seen = set()
    for lat in range(floor3(min_lat), floor3(max_lat) + 1, 3):
        for lon in range(floor3(min_lon), floor3(max_lon) + 1, 3):
            if (lat, lon) not in seen:
                seen.add((lat, lon))
                yield lat, lon


def dem_url(lat_tile: int, lon_tile: int) -> str:
    ns, lat_abs, ew, lon_abs = _ns_ew(lat_tile, lon_tile)
    name = f"Copernicus_DSM_COG_10_{ns}{lat_abs:02d}_00_{ew}{lon_abs:03d}_00_DEM"
    return f"{DEM_BASE}/{name}/{name}.tif"


def worldcover_url(lat_tile: int, lon_tile: int) -> str:
    ns, lat_abs, ew, lon_abs = _ns_ew(lat_tile, lon_tile)
    name = f"ESA_WorldCover_10m_2021_v200_{ns}{lat_abs:02d}{ew}{lon_abs:03d}_Map"
    return f"{WORLDCOVER_BASE}/{name}.tif"


def download(url: str, destination: Path) -> bool:
    """Downloads to a temp file, then atomically moves into place. Returns
    False (never raises) if the tile genuinely doesn't exist (404) — some
    bbox corners may not have a real tile (e.g. right at a coastline), and
    that's a real, reportable gap, not a crash."""
    if destination.exists():
        print(f"  already have {destination.name}, skipping")
        return True

    tmp_path = destination.with_suffix(destination.suffix + ".part")
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            if response.status_code == 404:
                print(f"  NOT FOUND: {url}")
                return False
            response.raise_for_status()
            destination.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
        tmp_path.rename(destination)
        print(f"  downloaded {destination.name} ({destination.stat().st_size / 1e6:.1f} MB)")
        return True
    except Exception as exc:  # noqa: BLE001 - report clearly, never crash the whole batch
        print(f"  FAILED: {url} -> {exc}")
        tmp_path.unlink(missing_ok=True)
        return False


def mosaic(paths, output_path: Path):
    import rasterio
    from rasterio.merge import merge

    datasets = [rasterio.open(p) for p in paths]
    try:
        merged, transform = merge(datasets)
        profile = datasets[0].profile
        profile.update(height=merged.shape[1], width=merged.shape[2], transform=transform)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(merged)
    finally:
        for ds in datasets:
            ds.close()


def main():
    parser = argparse.ArgumentParser(description="Download and mosaic real Copernicus DEM + ESA WorldCover tiles for a bbox")
    parser.add_argument("--min-lat", type=float, required=True)
    parser.add_argument("--min-lon", type=float, required=True)
    parser.add_argument("--max-lat", type=float, required=True)
    parser.add_argument("--max-lon", type=float, required=True)
    parser.add_argument("--raw-dir", default="data/raw/external/pilot_rasters")
    parser.add_argument("--dem-output", default="data/raw/external/pilot_dem.tif")
    parser.add_argument("--landcover-output", default="data/raw/external/pilot_landcover.tif")
    parser.add_argument("--skip-dem", action="store_true")
    parser.add_argument("--skip-landcover", action="store_true")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    dem_dir = raw_dir / "dem_tiles"
    landcover_dir = raw_dir / "landcover_tiles"

    if not args.skip_dem:
        print("=" * 60)
        print("DEM tiles (Copernicus DEM GLO-30)")
        print("=" * 60)
        tiles = list(dem_tile_ids(args.min_lat, args.min_lon, args.max_lat, args.max_lon))
        print(f"{len(tiles)} tile(s) needed for this bbox")
        downloaded = []
        for lat, lon in tiles:
            url = dem_url(lat, lon)
            dest = dem_dir / Path(url).name
            print(f"lat={lat} lon={lon}: {url}")
            if download(url, dest):
                downloaded.append(dest)
        print(f"\n{len(downloaded)}/{len(tiles)} DEM tile(s) downloaded successfully")
        if downloaded:
            print(f"Mosaicking into {args.dem_output} ...")
            mosaic(downloaded, Path(args.dem_output))
            print(f"Wrote {args.dem_output}")
        else:
            print("No DEM tiles available — nothing to mosaic.")

    if not args.skip_landcover:
        print("\n" + "=" * 60)
        print("Land cover tiles (ESA WorldCover 10m 2021 v200)")
        print("=" * 60)
        tiles = list(worldcover_tile_ids(args.min_lat, args.min_lon, args.max_lat, args.max_lon))
        print(f"{len(tiles)} tile(s) needed for this bbox")
        downloaded = []
        for lat, lon in tiles:
            url = worldcover_url(lat, lon)
            dest = landcover_dir / Path(url).name
            print(f"lat={lat} lon={lon}: {url}")
            if download(url, dest):
                downloaded.append(dest)
        print(f"\n{len(downloaded)}/{len(tiles)} land cover tile(s) downloaded successfully")
        if downloaded:
            print(f"Mosaicking into {args.landcover_output} ...")
            mosaic(downloaded, Path(args.landcover_output))
            print(f"Wrote {args.landcover_output}")
        else:
            print("No land cover tiles available — nothing to mosaic.")


if __name__ == "__main__":
    sys.exit(main())
