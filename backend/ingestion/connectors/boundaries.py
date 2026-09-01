"""Administrative boundary connector — thin status wrapper over
geospatial.india.boundary for the ingestion CLI. Point-in-polygon lookups
themselves live in that module since geospatial code (e.g.
ingestion/processors/landslides.py) also uses them directly.
"""
import os
from pathlib import Path
from typing import Optional

from geospatial.india.boundary import (
    ENV_DISTRICT_BOUNDARY_PATH,
    ENV_INDIA_BOUNDARY_PATH,
    ENV_STATE_BOUNDARY_PATH,
)
from ingestion.base import CONFIGURED, NOT_CONFIGURED, BaseConnector, ConnectorStatus

LEVEL_ENV_VARS = {
    "india": ENV_INDIA_BOUNDARY_PATH,
    "state": ENV_STATE_BOUNDARY_PATH,
    "district": ENV_DISTRICT_BOUNDARY_PATH,
}


class BoundaryConnector(BaseConnector):
    name = "boundaries"

    def __init__(self, level: str, manual_path: Optional[str] = None):
        if level not in LEVEL_ENV_VARS:
            raise ValueError(f"Unknown boundary level '{level}'. Expected one of {list(LEVEL_ENV_VARS)}.")
        self.level = level
        raw = manual_path or os.getenv(LEVEL_ENV_VARS[level])
        self.path = Path(raw) if raw else None

    def status(self) -> ConnectorStatus:
        if self.path is None:
            return ConnectorStatus(NOT_CONFIGURED, f"{LEVEL_ENV_VARS[self.level]} is not set.")
        if not self.path.exists():
            return ConnectorStatus(
                NOT_CONFIGURED, f"Configured {self.level} boundary path does not exist: {self.path.name}"
            )
        return ConnectorStatus(CONFIGURED, f"{self.level.title()} boundary file found.", local_path=self.path)
