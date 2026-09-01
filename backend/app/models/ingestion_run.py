from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class IngestionRun(Base):
    """One execution of scripts/ingest_dataset.py against a DataSource —
    an auditable processing log. `inserted` is only ever set to what was
    actually committed to the database, never assumed from valid_records.
    """

    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, nullable=False, index=True)

    total_records = Column(Integer, nullable=True)
    valid_records = Column(Integer, nullable=True)
    invalid_records = Column(Integer, nullable=True)
    inserted = Column(Integer, nullable=True)
    duplicates = Column(Integer, nullable=True)

    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    status = Column(String, nullable=False, default="processing")
    error_summary = Column(String, nullable=True)
