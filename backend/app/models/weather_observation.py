from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False, index=True)

    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    rainfall_24h = Column(Float, nullable=True)

    source = Column(String, nullable=True)
    observed_at = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
