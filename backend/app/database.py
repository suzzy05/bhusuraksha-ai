import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'bhusuraksha.db')}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# SQLite (local development, zero setup) is the default so `uvicorn
# app.main:app --reload` keeps working with no extra services. Set
# DATABASE_URL to a `postgresql+psycopg://` URL (see .env.example and
# docker-compose.yml) to use PostgreSQL + PostGIS instead — no code change
# needed, only configuration.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# True only when actually connected to PostgreSQL. Models use this to add
# PostGIS `geom` columns conditionally — GeoAlchemy2's Geometry type
# requires SpatiaLite on SQLite, which local development does not install,
# so those columns must not exist at all on the SQLite engine.
IS_POSTGRES = engine.dialect.name == "postgresql"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_status() -> dict:
    """Used by GET /health. Never returns the connection string or raw
    exception text — only connection/PostGIS status."""
    status = {"connected": False, "type": engine.dialect.name}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            status["connected"] = True
    except Exception:  # noqa: BLE001 - health check must never crash or leak internals
        return status

    if status["type"] == "postgresql":
        try:
            with engine.connect() as conn:
                version = conn.execute(text("SELECT PostGIS_Version()")).scalar()
            status["postgis"] = {"available": True, "version": version}
        except Exception:  # noqa: BLE001 - PostGIS may simply not be installed yet
            status["postgis"] = {"available": False}

    return status
