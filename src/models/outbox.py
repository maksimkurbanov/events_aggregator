from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, String, func, text, Index, Integer, CheckConstraint
from sqlalchemy import DateTime as saDateTime
from sqlalchemy.dialects.postgresql import UUID as pg_uuid, ENUM as pg_ENUM
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base_class import Base


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"


class Outbox(Base):
    __tablename__ = "outbox"

    id: Mapped[UUID] = mapped_column(
        pg_uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[OutboxStatus] = mapped_column(
        pg_ENUM(OutboxStatus), default=OutboxStatus.PENDING
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("retry_count >= 0", name="retry_count_non_negative"),
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        saDateTime(timezone=True), server_default=func.timezone("UTC", func.now())
    )
    updated_at: Mapped[datetime] = mapped_column(
        saDateTime(timezone=True),
        server_default=func.timezone("UTC", func.now()),
        server_onupdate=func.timezone("UTC", func.now()),
    )

    __table_args__ = (
        Index(
            "ix_outbox_status",
            "status",
            "created_at",
            postgresql_where=text("status = 'PENDING'"),
        ),
    )
