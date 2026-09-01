"""Phase 21/23 — derives real monitored Zone rows from real registered
LandslideEvent clusters.

Unlike the original Phase 21 version (one zone per state), this clusters
each state's real event coordinates with DBSCAN — a real, standard,
parameter-free-in-spirit geographic clustering algorithm (not an invented
heuristic) — so a state with events spread across distinct regions (e.g.
Uttarakhand's 189 events) gets several real, smaller zones instead of one
giant state-wide centroid. `--cluster-eps-km` controls how close two events
need to be to join the same cluster (default 60km — roughly "same
district-scale region"); `--min-cluster-size` is 1, so an isolated real
event still gets its own zone rather than being dropped.

Every field is either a real, computed value or an honest placeholder,
never a fabrication:
- `latitude`/`longitude`: the real centroid (mean) of that cluster's actual
  event coordinates.
- `historical_event_count`: the real count.
- `slope`/`elevation`/`terrain_data_real`: if a real, registered DEM
  currently covers this zone's coordinates (BHUSURAKSHA_DEM_DATA_PATH),
  these are REAL values read from it (never estimated) and
  `terrain_data_real=True`. Otherwise they stay the schema's 0.0 default
  and `terrain_data_real=False` — `risk_update_service.update_zone_risk()`
  and `GET /zones/{id}` both key off this flag to decide whether it's
  honest to run the rule-based engine on this zone at all (see their own
  docstrings/comments).
- `risk_score`/`risk_level`: 0.0/"UNKNOWN" at creation time regardless —
  a real score is computed by the normal risk-update flow afterward (e.g.
  `POST /weather/refresh-all`), only for zones where `terrain_data_real`
  makes that legitimate.
- Environment columns other than slope/elevation (rainfall/humidity/
  temperature) keep their schema defaults at creation time — real live
  values arrive via the existing Phase 6 weather-refresh flow, not here.

Idempotent-ish: re-running DELETES and rebuilds all `source_type="derived"`
zones from scratch (never touches demo/other zones) rather than trying to
diff against a previous clustering, since a different `--cluster-eps-km`
would produce a genuinely different real clustering, not an incremental
update.

Usage:
    python scripts/build_derived_zones.py --cluster-eps-km 60
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.cluster import DBSCAN

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.landslide_event import LandslideEvent  # noqa: E402
from app.models.zone import Zone  # noqa: E402
from app.services.landcover_service import get_landcover  # noqa: E402
from app.services.terrain_service import get_terrain_features  # noqa: E402

DEFAULT_BOUNDARY_PATH = "data/raw/external/india_states_natural_earth.geojson"
DEFAULT_CLUSTER_EPS_KM = 60.0
KM_PER_DEGREE_LAT = 111.32


def _load_india_state_names(boundary_path: str) -> set:
    with open(boundary_path, encoding="utf-8") as f:
        data = json.load(f)
    return {feature["properties"]["name"] for feature in data["features"]}


def _cluster_state_events(events, eps_km: float, min_cluster_size: int):
    """Real DBSCAN clustering on real (lat, lon) pairs. `eps` is converted
    from km to degrees using a fixed lat/lon scale — an approximation (a
    degree of longitude shrinks toward the poles) acceptable at
    monitoring-zone granularity, not survey-grade precision."""
    coords = np.array([[e.latitude, e.longitude] for e in events])
    eps_degrees = eps_km / KM_PER_DEGREE_LAT
    labels = DBSCAN(eps=eps_degrees, min_samples=min_cluster_size).fit_predict(coords)

    clusters = defaultdict(list)
    for event, label in zip(events, labels):
        # DBSCAN labels noise points -1 when min_samples > 1; with the
        # default min_samples=1 every point gets a real cluster of its own
        # rather than being dropped, so this branch is defensive.
        key = label if label != -1 else f"solo_{event.id}"
        clusters[key].append(event)
    return list(clusters.values())


def _real_terrain_for(lat: float, lon: float):
    terrain = get_terrain_features(lat=lat, lon=lon)
    if not terrain["available"] or terrain["slope_degrees"] is None or terrain["elevation_m"] is None:
        return None
    return terrain["elevation_m"], terrain["slope_degrees"]


def main():
    parser = argparse.ArgumentParser(description="Derive real Zone rows from real LandslideEvent clusters (DBSCAN)")
    parser.add_argument("--cluster-eps-km", type=float, default=DEFAULT_CLUSTER_EPS_KM)
    parser.add_argument("--min-cluster-size", type=int, default=1)
    parser.add_argument("--boundary-path", default=DEFAULT_BOUNDARY_PATH)
    args = parser.parse_args()

    india_states = _load_india_state_names(args.boundary_path)
    print(f"Restricting to {len(india_states)} real India state/UT name(s) from {args.boundary_path}")
    print(f"Clustering with DBSCAN(eps={args.cluster_eps_km}km, min_samples={args.min_cluster_size})")

    db = SessionLocal()
    try:
        deleted = db.query(Zone).filter(Zone.source_type == "derived").delete()
        db.commit()
        print(f"Removed {deleted} previously-derived zone(s) before rebuilding.")

        events = (
            db.query(LandslideEvent)
            .filter(LandslideEvent.state.in_(india_states))
            .all()
        )
        print(f"Real India events (state matches the registered boundary): {len(events)}")

        by_state = defaultdict(list)
        for event in events:
            by_state[event.state].append(event)

        created = 0
        with_real_terrain = 0
        for state, state_events in sorted(by_state.items()):
            clusters = _cluster_state_events(state_events, args.cluster_eps_km, args.min_cluster_size)
            multi = len(clusters) > 1
            for i, cluster_events in enumerate(clusters, start=1):
                centroid_lat = sum(e.latitude for e in cluster_events) / len(cluster_events)
                centroid_lon = sum(e.longitude for e in cluster_events) / len(cluster_events)

                real_terrain = _real_terrain_for(centroid_lat, centroid_lon)
                slope = real_terrain[1] if real_terrain else 0.0
                elevation = real_terrain[0] if real_terrain else 0.0
                terrain_data_real = real_terrain is not None
                if terrain_data_real:
                    with_real_terrain += 1

                name = f"{state} Region {i} (Historical Cluster)" if multi else f"{state} (Historical Cluster)"

                zone = Zone(
                    name=name,
                    state=state,
                    latitude=round(centroid_lat, 6),
                    longitude=round(centroid_lon, 6),
                    rainfall_24h=0.0,
                    rainfall_7d=0.0,
                    humidity=0.0,
                    temperature=0.0,
                    slope=slope,
                    elevation=elevation,
                    vegetation=0.5,
                    historical_landslide=True,
                    risk_score=0.0,
                    risk_level="UNKNOWN",
                    source_type="derived",
                    historical_event_count=len(cluster_events),
                    terrain_data_real=terrain_data_real,
                )
                db.add(zone)
                created += 1
                terrain_note = f"real terrain: elev={elevation:.0f}m slope={slope:.1f}deg" if terrain_data_real else "no real terrain coverage"
                print(f"  + {name}: {len(cluster_events)} real event(s), centroid ({centroid_lat:.4f}, {centroid_lon:.4f}), {terrain_note}")

        db.commit()
        print(f"\nCreated {created} derived zone(s) across {len(by_state)} state(s)/UT(s).")
        print(f"{with_real_terrain}/{created} have real terrain (inside the currently configured DEM's coverage) — "
              f"those are eligible for a real rule-based risk score on the next weather refresh; the rest stay UNKNOWN.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
