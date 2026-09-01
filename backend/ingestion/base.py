"""Common connector contract.

Every connector in ingestion/connectors/ exposes a `status()` method
returning one of the states below, and — where a download even makes
sense — a `download()` method that only ever runs when a caller
explicitly invokes it. Nothing in this package downloads or ingests
anything automatically or on import.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

NOT_CONFIGURED = "not_configured"
CONFIGURED = "configured"
CREDENTIALS_REQUIRED = "credentials_required"
DOWNLOAD_FAILED = "download_failed"


@dataclass
class ConnectorStatus:
    state: str
    message: str
    local_path: Optional[Path] = None


class BaseConnector:
    name = "base"

    def status(self) -> ConnectorStatus:
        raise NotImplementedError

    def download(self, destination: Path) -> ConnectorStatus:
        raise NotImplementedError(f"The '{self.name}' connector does not support downloading.")
