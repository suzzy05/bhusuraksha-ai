from fastapi import APIRouter

from app.database import get_database_status

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description="Reports service and database status. Never exposes connection strings, credentials, or exception internals.",
)
def health_check():
    database = get_database_status()
    status = "healthy" if database["connected"] else "degraded"
    return {"status": status, "service": "BHUSURAKSHA AI Backend", "database": database}
