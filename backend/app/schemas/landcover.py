from typing import Optional

from pydantic import BaseModel


class LandcoverResponse(BaseModel):
    available: bool
    raw_class: Optional[int] = None
    normalized_category: Optional[str] = None
    scheme: Optional[str] = None
    message: str
