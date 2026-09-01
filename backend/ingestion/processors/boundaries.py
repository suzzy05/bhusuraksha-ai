"""Administrative boundary dataset processing: validates that the file
parses as real GeoJSON and reports its feature count. GeoPackage is
reported as unsupported unless the optional 'fiona'/'geopandas' dependency
is actually installed — no fabricated geometries either way.
"""
import json
from pathlib import Path


def process_boundary_dataset(path: Path) -> dict:
    suffix = path.suffix.lower()

    if suffix == ".gpkg":
        try:
            import fiona  # noqa: F401
        except ImportError:
            return {
                "available": False,
                "reason": "GeoPackage support requires the optional 'fiona' package, which is not installed.",
            }
        return {"available": False, "reason": "GeoPackage reading is not yet implemented in this phase."}

    if suffix not in (".geojson", ".json"):
        return {"available": False, "reason": f"Unsupported boundary format: {suffix or '(none)'}"}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return {"available": False, "reason": f"Could not parse GeoJSON: {exc}"}

    features = data.get("features", []) if isinstance(data, dict) else []
    return {"available": True, "feature_count": len(features)}
