"""IMD (India Meteorological Department) rainfall connector.

Automated bulk IMD downloads are not assumed to be permitted — this
connector only supports a manually-provided local file, via
BHUSURAKSHA_IMD_RAINFALL_PATH or an explicit path. No download method.
"""
import os
from pathlib import Path
from typing import Optional

from ingestion.base import CONFIGURED, NOT_CONFIGURED, BaseConnector, ConnectorStatus

ENV_PATH = "BHUSURAKSHA_IMD_RAINFALL_PATH"


def _env_path() -> Optional[Path]:
    raw = os.getenv(ENV_PATH)
    return Path(raw) if raw else None


class ImdRainfallConnector(BaseConnector):
    name = "imd_rainfall"

    def __init__(self, manual_path: Optional[str] = None):
        self.path = Path(manual_path) if manual_path else _env_path()

    def status(self) -> ConnectorStatus:
        if self.path is None:
            return ConnectorStatus(NOT_CONFIGURED, f"{ENV_PATH} is not set and no path was given.")
        if not self.path.exists():
            return ConnectorStatus(NOT_CONFIGURED, f"Configured path does not exist: {self.path.name}")
        return ConnectorStatus(CONFIGURED, "Rainfall dataset file found.", local_path=self.path)
