from pydantic import BaseModel
from typing import Any


class OutboxCreate(BaseModel):
    event_type: str
    payload: dict[str, Any]
