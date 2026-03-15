from datetime import datetime
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as pg_uuid
from sqlalchemy.orm import Mapped
from sqlalchemy.testing.schema import mapped_column

from src.models.base_class import Base


class Ticket(Base):
    __tablename__ = "ticket"

    ticket_id: Mapped[UUID] = mapped_column(pg_uuid, primary_key=True)
    event_id: Mapped[UUID] = mapped_column(pg_uuid)
    seat: Mapped[str] = mapped_column(String)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    email: Mapped[EmailStr] = mapped_column(String)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.timezone("UTC", func.now())
    )
