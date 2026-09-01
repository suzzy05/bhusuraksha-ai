"""DEM (Digital Elevation Model) connector.

Supports a manually-configured GeoTIFF via BHUSURAKSHA_DEM_PATH. Reading
raster metadata requires the optional 'rasterio' package, which is
deliberately NOT part of this project's base requirements (avoiding a
heavy GIS dependency stack per Phase 9's scope) — if it isn't installed,
this reports that plainly rather than faking support.
"""
import os
from pathlib import Path
from typing import Optional

from ingestion.base import CONFIGURED, NOT_CONFIGURED, BaseConnector, ConnectorStatus

ENV_PATH = "BHUSURAKSHA_DEM_PATH"


def raster_backend_available() -> bool:
    try:
        import rasterio  # noqa: F401

        return True
    except ImportError:
        return False


class DemConnector(BaseConnector):
    name = "dem"

    def __init__(self, manual_path: Optional[str] = None):
        raw = manual_path or os.getenv(ENV_PATH)
        self.path = Path(raw) if raw else None

    def status(self) -> ConnectorStatus:
        if self.path is None:
            return ConnectorStatus(NOT_CONFIGURED, f"{ENV_PATH} is not set.")
        if not self.path.exists():
            return ConnectorStatus(NOT_CONFIGURED, f"Configured DEM path does not exist: {self.path.name}")
        if not raster_backend_available():
            return ConnectorStatus(
                NOT_CONFIGURED,
                "DEM file is configured, but reading GeoTIFF metadata requires the optional 'rasterio' "
                "package, which is not installed here. Install it (`pip install rasterio`) to enable DEM ingestion.",
            )
        return ConnectorStatus(CONFIGURED, "DEM file found and rasterio is available.", local_path=self.path)

    def extract_metadata(self) -> dict:
        """CRS, resolution, bounding box, nodata, dimensions — only ever
        read from the actual file via rasterio, never estimated."""
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
                "nodata": dataset.nodata,
            }
