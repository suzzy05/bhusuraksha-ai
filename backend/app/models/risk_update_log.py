from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base


class RiskUpdateLog(Base):
    """An audit row for one risk recomputation — Phase 16. Records exactly
    what inputs were used and where the prediction came from, so a risk
    score can always be explained after the fact, not just displayed.
    Never deleted; history grows monotonically.
    """

    __tablename__ = "risk_update_logs"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False, index=True)

    # "manual_refresh" (POST /weather/{id}/refresh), "manual_refresh_all"
    # (POST /weather/refresh-all), or "scheduled_worker" (scripts/run_scheduled_risk_update.py)
    triggered_by = Column(String, nullable=False)

    inputs = Column(JSON, nullable=False)
    data_availability = Column(JSON, nullable=False)

    prediction_source = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
