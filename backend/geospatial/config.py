"""Configuration for external (real-world) geospatial datasets.

Every path is optional and read from an environment variable — nothing
here downloads data or requires an API key. If a variable is unset, the
corresponding dataset is simply treated as "not configured" and the
pipeline continues without it (see pipeline.run_pipeline_from_config).
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ENV_LANDSLIDE_PATH = "BHUSURAKSHA_LANDSLIDE_DATA_PATH"
ENV_RAINFALL_PATH = "BHUSURAKSHA_RAINFALL_DATA_PATH"
ENV_DEM_PATH = "BHUSURAKSHA_DEM_DATA_PATH"
ENV_VEGETATION_PATH = "BHUSURAKSHA_VEGETATION_DATA_PATH"

NOT_CONFIGURED_MESSAGE = "External dataset not configured."


def _resolve_path(env_var: str) -> Optional[Path]:
    raw = os.getenv(env_var)
    if not raw:
        return None
    return Path(raw)


@dataclass
class ExternalDataConfig:
    landslide_path: Optional[Path]
    rainfall_path: Optional[Path]
    dem_path: Optional[Path]
    vegetation_path: Optional[Path]

    def is_configured(self, name: str) -> bool:
        return getattr(self, f"{name}_path") is not None

    def status(self) -> dict:
        """Configuration status only — deliberately never includes the
        actual filesystem paths, so this is safe to expose via an API."""
        return {name: {"configured": self.is_configured(name)} for name in ("landslide", "rainfall", "dem", "vegetation")}


def load_external_data_config() -> ExternalDataConfig:
    return ExternalDataConfig(
        landslide_path=_resolve_path(ENV_LANDSLIDE_PATH),
        rainfall_path=_resolve_path(ENV_RAINFALL_PATH),
        dem_path=_resolve_path(ENV_DEM_PATH),
        vegetation_path=_resolve_path(ENV_VEGETATION_PATH),
    )
