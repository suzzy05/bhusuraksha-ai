"""Land cover / vegetation classification connector.

Supports a manually-configured GeoTIFF via BHUSURAKSHA_LANDCOVER_PATH.
Like dem.py, reading raster metadata requires the optional 'rasterio'
package — reported plainly as unavailable if it isn't installed. Year and
classification-scheme metadata come from explicit registration arguments
(scripts/ingest_dataset.py), never invented from the raster itself.
"""
import os
from pathlib import Path
from typing import Optional

from ingestion.base import CONFIGURED, NOT_CONFIGURED, BaseConnector, ConnectorStatus
from ingestion.connectors.dem import raster_backend_available

ENV_PATH = "BHUSURAKSHA_LANDCOVER_PATH"


class LandcoverConnector(BaseConnector):
    name = "landcover"

    def __init__(self, manual_path: Optional[str] = None):
        raw = manual_path or os.getenv(ENV_PATH)
        self.path = Path(raw) if raw else None

    def status(self) -> ConnectorStatus:
        if self.path is None:
            return ConnectorStatus(NOT_CONFIGURED, f"{ENV_PATH} is not set.")
        if not self.path.exists():
            return ConnectorStatus(NOT_CONFIGURED, f"Configured land cover path does not exist: {self.path.name}")
        if not raster_backend_available():
            return ConnectorStatus(
                NOT_CONFIGURED,
                "Land cover file is configured, but reading GeoTIFF metadata requires the optional "
                "'rasterio' package, which is not installed here.",
            )
        return ConnectorStatus(CONFIGURED, "Land cover file found and rasterio is available.", local_path=self.path)

    def extract_metadata(self) -> dict:
        status = self.status()
        if status.state != CONFIGURED:
            return {"available": False, "reason": status.message}

        import rasterio

        with rasterio.open(self.path) as dataset:
            return {
                "available": True,
                "crs": str(dataset.crs) if dataset.crs else None,
                "width": dataset.width,
                "height": dataset.height,
                "resolution": list(dataset.res),
                "bounding_box": list(dataset.bounds),
            }
