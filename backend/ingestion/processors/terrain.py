"""DEM (terrain) dataset processing: extracts and returns real raster
metadata for provenance storage. Does not compute slope/elevation for all
of India, and does not run without the optional 'rasterio' dependency —
see ingestion/connectors/dem.py and geospatial/terrain.py.
"""
from pathlib import Path

from ingestion.connectors.dem import DemConnector


def process_dem_dataset(path: Path) -> dict:
    return DemConnector(manual_path=str(path)).extract_metadata()
