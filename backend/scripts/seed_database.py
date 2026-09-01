"""Explicit, idempotent demo-data seeding entry point.

Usage:
    python scripts/seed_database.py

Safe to run any number of times: it reuses the same idempotent
app.services.seed_service functions the app itself calls on startup (they
no-op once zones already exist), so running this twice never duplicates
the 7 demo zones or their alerts. It never touches WeatherObservation
history or LandslideEvent records — seeding only ever adds Zone/Alert rows
for the fixed demo set.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine  # noqa: E402
from app.models.zone import Zone  # noqa: E402
from app.services.seed_service import generate_alerts, seed_zones  # noqa: E402


def main():
    db = SessionLocal()
    try:
        before = db.query(Zone).count()
        seed_zones(db)
        generate_alerts(db)
        after = db.query(Zone).count()
    finally:
        db.close()

    print("=" * 60)
    print("BHUSURAKSHA AI - DATABASE SEED")
    print("=" * 60)
    print(f"Database: {engine.dialect.name}")
    print(f"Zones before: {before}")
    print(f"Zones after: {after}")
    if before == after and before > 0:
        print("Zones already seeded — no duplicates created (idempotent).")
    else:
        print(f"Seeded {after - before} demo zone(s), each tagged source_type=\"demo_seed\".")
    print("Alerts reconciled for any HIGH/CRITICAL zones (duplicates prevented).")


if __name__ == "__main__":
    main()
