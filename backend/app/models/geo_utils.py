"""Keeps a PostGIS `geom` column in sync with a model's `latitude`/
`longitude` columns on insert/update. Only used when actually running
against PostgreSQL — see app.database.IS_POSTGRES; callers only invoke
this inside an `if IS_POSTGRES:` block.
"""
from sqlalchemy import event


def sync_point_geometry(model) -> None:
    from geoalchemy2.elements import WKTElement

    def _sync(mapper, connection, target):
        if target.latitude is not None and target.longitude is not None:
            # WKT point order is (longitude latitude) — X before Y. Never swap these.
            target.geom = WKTElement(f"POINT({target.longitude} {target.latitude})", srid=4326)

    event.listen(model, "before_insert", _sync)
    event.listen(model, "before_update", _sync)
