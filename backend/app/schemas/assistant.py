from typing import Any, Dict

from pydantic import BaseModel


class AssistantAnswer(BaseModel):
    answer: str
    intent: str
    data: Dict[str, Any]
