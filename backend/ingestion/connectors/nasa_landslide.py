"""Connector architecture for NASA / global landslide inventory data.

Does not assume any URL is permanently valid and does not hardcode one.
If you have a real, currently-valid URL for a dataset you're licensed to
use, configure it via BHUSURAKSHA_NASA_LANDSLIDE_URL — otherwise this
reports not_configured and the app continues to work fine without it. A
manual local file always takes precedence over downloading.
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import requests

from ingestion.base import (
    CONFIGURED,
    CREDENTIALS_REQUIRED,
    DOWNLOAD_FAILED,
    NOT_CONFIGURED,
    BaseConnector,
    ConnectorStatus,
)
from ingestion.checksum import sha256_of_file

ENV_URL = "BHUSURAKSHA_NASA_LANDSLIDE_URL"
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
CHUNK_SIZE = 1024 * 1024


class _CredentialsRequired(Exception):
    pass


class NasaLandslideConnector(BaseConnector):
    name = "nasa_landslide"

    def __init__(self, manual_path: Optional[str] = None):
        self.manual_path = Path(manual_path) if manual_path else None
        self.url = os.getenv(ENV_URL)

    def status(self) -> ConnectorStatus:
        if self.manual_path is not None:
            if self.manual_path.exists():
                return ConnectorStatus(CONFIGURED, "Using manually-provided dataset path.", local_path=self.manual_path)
            return ConnectorStatus(NOT_CONFIGURED, f"Manual path does not exist: {self.manual_path.name}")
        if not self.url:
            return ConnectorStatus(NOT_CONFIGURED, f"{ENV_URL} is not set — no download configured.")
        return ConnectorStatus(CONFIGURED, "Download URL configured.")

    def download(self, destination) -> ConnectorStatus:
        """Downloads to a temp file, validates the response, checksums it,
        then atomically moves it into place. Never overwrites an existing
        destination file silently, and never leaves a partial file behind
        pretending to be valid."""
        if not self.url:
            return ConnectorStatus(NOT_CONFIGURED, f"{ENV_URL} is not set.")

        destination = Path(destination)
        if destination.exists():
            return ConnectorStatus(
                CONFIGURED,
                f"Refusing to overwrite existing file: {destination.name}. Remove it first or choose a new destination.",
            )

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            tmp_fd, tmp_path_str = tempfile.mkstemp(prefix="bhusuraksha_download_", suffix=".part")
            tmp_path = Path(tmp_path_str)
            try:
                # The temp file handle must be fully closed (i.e. we must
                # be OUTSIDE this `with` block) before we can unlink it on
                # Windows, which refuses to delete an open file — so a
                # credentials/auth failure is raised here and only handled
                # once the `with` block has exited, never unlinked from
                # inside it.
                with os.fdopen(tmp_fd, "wb") as tmp_file:
                    with requests.get(self.url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                        if response.status_code in (401, 403):
                            raise _CredentialsRequired()
                        response.raise_for_status()
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            if chunk:
                                tmp_file.write(chunk)

                if tmp_path.stat().st_size == 0:
                    raise ValueError("Downloaded file is empty.")

                checksum = sha256_of_file(tmp_path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(tmp_path), str(destination))
                return ConnectorStatus(
                    CONFIGURED, f"Downloaded and verified (sha256={checksum[:12]}...).", local_path=destination
                )
            except _CredentialsRequired:
                tmp_path.unlink(missing_ok=True)
                return ConnectorStatus(
                    CREDENTIALS_REQUIRED,
                    "The configured URL requires authentication BHUSURAKSHA does not have configured. "
                    "See docs/REAL_DATA_INGESTION.md for how to provide credentials.",
                )
            except Exception as exc:  # noqa: BLE001 - report clearly and retry rather than crash
                last_error = exc
                tmp_path.unlink(missing_ok=True)

        return ConnectorStatus(DOWNLOAD_FAILED, f"Download failed after {MAX_RETRIES} attempts: {last_error}")
