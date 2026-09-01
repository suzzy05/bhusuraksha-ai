from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.assistant import AssistantAnswer
from app.services.assistant_service import answer_question

router = APIRouter(tags=["Assistant"])


@router.get(
    "/assistant/ask",
    response_model=AssistantAnswer,
    summary="Real-data-grounded question answering (Phase 25)",
    description=(
        "Answers a small set of real, common questions (riskiest place, is a place safe, active alerts, "
        "weather, historical event counts) entirely from real database queries — no LLM, no API key, no "
        "invented facts. An unrecognized question returns guidance on what it can answer, never a guess."
    ),
)
def ask_assistant(q: str = Query(..., min_length=1, max_length=500), db: Session = Depends(get_db)):
    return answer_question(db, q)
