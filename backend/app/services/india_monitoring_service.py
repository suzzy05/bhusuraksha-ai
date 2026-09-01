"""Shared helpers for Phase 7's pan-India monitoring summary, used by both
GET /india/summary and the `india_monitoring` block of GET /data-status —
kept in one place so the two never disagree.
"""
from sqlalchemy.orm import Session

from app.models.landslide_event import LandslideEvent
from app.models.monitoring_region import MonitoringRegion
from app.models.zone import Zone
from geospatial.source_registry import list_sources


def coverage_status(regions_with_real_data: int, historical_events: int) -> str:
    """A deliberately conservative, documented heuristic — never claims
    broader coverage than the actual counts support. Coverage here means
    DATA coverage, not landslide risk."""
    if regions_with_real_data == 0 and historical_events == 0:
        return "prototype"
    if regions_with_real_data < 5 and historical_events < 50:
        return "partial_real_data"
    if regions_with_real_data < 50:
        return "regional_real_data"
    return "expanded_real_data"


def get_summary(db: Session) -> dict:
    monitoring_regions = db.query(MonitoringRegion).count()
    regions_with_real_data = (
        db.query(MonitoringRegion).filter(MonitoringRegion.source_type == "external_real").count()
    )
    # Total real Zone rows monitored — a mix of Phase 1 reference (demo_seed)
    # zones and Phase 21+ zones derived from real historical event clusters;
    # see each zone's own source_type for which it is.
    total_zones = db.query(Zone).count()
    historical_landslide_events = db.query(LandslideEvent).count()

    return {
        "monitoring_regions": monitoring_regions,
        "regions_with_real_data": regions_with_real_data,
        "total_zones": total_zones,
        "historical_landslide_events": historical_landslide_events,
        "coverage_status": coverage_status(regions_with_real_data, historical_landslide_events),
        "registered_data_sources": len(list_sources(db)),
    }
