"""Common internal record schema that every geospatial data source is
normalized into, regardless of whether it came from the demo synthetic
dataset or a real external one.

Missing values are kept as `None` rather than invented — a field that the
source dataset doesn't provide stays missing all the way through the
pipeline.
"""
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import List, Optional


class SourceType(str, Enum):
    DEMO = "demo_synthetic"
    EXTERNAL = "external_real"


@dataclass
class GeoRiskRecord:
    location_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    event_date: Optional[str] = None

    rainfall_24h: Optional[float] = None
    rainfall_7d: Optional[float] = None

    humidity: Optional[float] = None
    temperature: Optional[float] = None

    elevation: Optional[float] = None
    slope: Optional[float] = None
    vegetation: Optional[float] = None

    historical_landslide: Optional[bool] = None

    # Only ever set for records with a scientifically valid label. Real
    # external records are never assigned a fabricated risk_level.
    risk_level: Optional[str] = None

    source_type: str = SourceType.EXTERNAL.value
    source_name: Optional[str] = None

    # Data COMPLETENESS, not landslide risk — see feature_engineering.calculate_data_quality.
    data_quality_score: Optional[float] = None
    missing_features: List[str] = field(default_factory=list)

    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# The feature set the Phase 2 ML model was trained on. The geospatial
# pipeline's processed output targets these same names so a future phase
# can align real data onto the existing model/feature set without a schema
# rewrite (see docs/DATA_SOURCES.md, "ML integration preparation").
ML_FEATURE_FIELDS = [
    "rainfall_24h",
    "rainfall_7d",
    "humidity",
    "temperature",
    "slope",
    "elevation",
    "vegetation",
    "historical_landslide",
]
