"""Ingestion-specific validation.

Coordinate range validation is reused as-is from geospatial.validators
(Phase 3) rather than duplicated — this module adds what's specific to
Phase 9 ingestion: safe multi-format date parsing that never guesses.
"""
from datetime import datetime
from typing import Optional

from geospatial.validators import validate_coordinates  # noqa: F401 - re-exported for processors

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y%m%d",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
)


def parse_date_safely(value) -> Optional[datetime]:
    """Tries ISO parsing plus a fixed set of common formats. Returns None
    — never a fabricated/guessed date — if nothing matches."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none", "null"):
        return None

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None
