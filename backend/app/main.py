import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import Base, SessionLocal, engine
from app.logging_config import configure_logging
from app.routes import (
    alerts,
    assistant,
    data_sources,
    data_status,
    features,
    health,
    india,
    landcover,
    landslides,
    rainfall,
    regions,
    risk,
    susceptibility,
    terrain,
    weather,
    zones,
)
from app.services.seed_service import generate_alerts, seed_zones

configure_logging()
logger = logging.getLogger(__name__)

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BHUSURAKSHA AI backend (database dialect: %s)", engine.dialect.name)

    if engine.dialect.name == "sqlite":
        # Local SQLite development: zero-friction auto-create, matching
        # existing behavior from earlier phases. PostgreSQL deployments use
        # Alembic migrations instead (see backend/alembic/,
        # docs/DEPLOYMENT.md) — this deliberately does not run against
        # Postgres so migrations remain the single source of schema truth
        # there.
        Base.metadata.create_all(bind=engine)
        logger.info("SQLite schema ensured via create_all()")
    else:
        logger.info("PostgreSQL detected — schema is managed by Alembic migrations, not create_all()")

    try:
        with engine.connect():
            logger.info("Database connection established")
    except Exception:
        logger.exception("Database connection failed at startup")
        raise

    db = SessionLocal()
    try:
        seed_zones(db)
        generate_alerts(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title="BHUSURAKSHA AI",
    description="Predict. Warn. Protect. — AI-powered landslide early warning and risk monitoring platform.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allows the frontend (Vite dev server locally, or the Nginx-served
# container in Docker) to call this API from the browser. Configurable via
# CORS_ALLOWED_ORIGINS (comma-separated) for deployment; defaults to the
# local dev origins so nothing changes for existing developers.
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid request data", "details": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak internal exception details (stack traces, DB errors, etc.)
    # to clients — full details still go to the server logs.
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


app.include_router(health.router)
app.include_router(zones.router)
app.include_router(alerts.router)
app.include_router(risk.router)
app.include_router(data_status.router)
app.include_router(weather.router)
app.include_router(landslides.router)
app.include_router(rainfall.router)
app.include_router(terrain.router)
app.include_router(landcover.router)
app.include_router(features.router)
app.include_router(susceptibility.router)
app.include_router(assistant.router)
app.include_router(regions.router)
app.include_router(india.router)
app.include_router(data_sources.router)
