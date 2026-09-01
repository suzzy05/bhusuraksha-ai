"""The manual connector — the FIRST reliable ingestion mechanism: the user
already has a file on disk and points scripts/ingest_dataset.py at it
directly via --path. No network access, no assumptions.
"""
from pathlib import Path
from typing import Optional

from ingestion.base import CONFIGURED, NOT_CONFIGURED, BaseConnector, ConnectorStatus


class ManualConnector(BaseConnector):
    name = "manual"

    def __init__(self, path: Optional[str]):
        self.path = Path(path) if path else None

    def status(self) -> ConnectorStatus:
        if self.path is None:
            return ConnectorStatus(NOT_CONFIGURED, "No path provided.")
        if not self.path.exists():
            return ConnectorStatus(NOT_CONFIGURED, f"File not found: {self.path.name}")
        return ConnectorStatus(CONFIGURED, "File found and ready to inspect.", local_path=self.path)
