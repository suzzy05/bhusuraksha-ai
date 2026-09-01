from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from app.database import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    state = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    rainfall_24h = Column(Float, nullable=False, default=0.0)
    rainfall_7d = Column(Float, nullable=False, default=0.0)

    humidity = Column(Float, nullable=False, default=0.0)
    temperature = Column(Float, nullable=False, default=0.0)

    slope = Column(Float, nullable=False, default=0.0)
    elevation = Column(Float, nullable=False, default=0.0)
    vegetation = Column(Float, nullable=False, default=0.5)

    historical_landslide = Column(Boolean, nullable=False, default=False)

    risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String, nullable=False, default="LOW")

    # Data provenance: "demo_seed" (Phase 1 seeded demo zones), "external_real"
    # (from an actual registered dataset), or "derived" (computed from other
    # records). All zones seeded by app/services/seed_service.py are demo_seed.
    source_type = Column(String, nullable=False, default="demo_seed")

    # Phase 21 — real count of registered LandslideEvent rows this zone was
    # derived from (source_type="derived" only). NULL for demo/other zones.
    # risk_score/risk_level are NEVER computed from this — the rule-based
    # engine needs real rainfall/slope/etc. this project doesn't have for
    # most of India, so a derived zone's risk_level is honestly "UNKNOWN"
    # (risk_score 0.0) rather than fabricated from placeholder inputs.
    historical_event_count = Column(Integer, nullable=True)

    # Phase 23 — True only once slope/elevation were actually replaced with
    # real values read from a real, registered DEM (never guessed) for this
    # zone's real coordinates. A derived zone with this False still has the
    # 0.0 schema-default placeholders in `slope`/`elevation` — risk stays
    # honestly UNKNOWN for those. Once True, the zone has real terrain +
    # real live rainfall/humidity (Phase 6 weather refresh) + real
    # historical_landslide=True — enough real inputs that the normal rule-
    # based engine is no longer fabricating a score from placeholders, so
    # update_zone_risk() stops treating it as a no-op.
    terrain_data_real = Column(Boolean, nullable=False, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
