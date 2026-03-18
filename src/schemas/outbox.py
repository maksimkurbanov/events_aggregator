from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from typing import Any

from src.models.outbox import OutboxStatus


class OutboxInDB(BaseModel):
    id: UUID
    event_type: str
    payload: dict[str, Any]
    status: OutboxStatus
    created_at: datetime
    updated_at: datetime


class OutboxCreate(BaseModel):
    event_type: str
    payload: dict[str, Any]


class OutboxUpdate(BaseModel):
    status: OutboxStatus | None = None
    retry_count: int | None = Field(default=0, ge=0)
