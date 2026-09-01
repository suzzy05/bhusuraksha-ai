"""Shared plain dataclasses for ingestion results — used by processors
and printed/logged by scripts/ingest_dataset.py.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class RejectedRecord:
    index: int
    reasons: List[str]
    raw: dict


@dataclass
class IngestionSummary:
    source_id: str
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    inserted: int = 0
    duplicates: int = 0
    rejected: List[RejectedRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "inserted": self.inserted,
            "duplicates": self.duplicates,
        }
