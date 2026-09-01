"""Land cover dataset processing: extracts real raster metadata; year and
classification scheme come from explicit CLI arguments, never invented
from the raster itself.
"""
from pathlib import Path
from typing import Optional

from ingestion.connectors.landcover import LandcoverConnector


def process_landcover_dataset(path: Path, year: Optional[str] = None, classification: Optional[str] = None) -> dict:
    metadata = LandcoverConnector(manual_path=str(path)).extract_metadata()
    if metadata.get("available"):
        metadata["year"] = year
        metadata["classification"] = classification
    return metadata
