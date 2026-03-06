from datetime import datetime
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as pg_uuid
from sqlalchemy.orm import Mapped

from src.models.base_class import Base


class Ticket(Base):
    __tablename__ = "ticket"

    ticket_id: Mapped[UUID] = Column(pg_uuid, primary_key=True)
    event_id: Mapped[UUID] = Column(pg_uuid)
    seat: Mapped[str] = Column(String, nullable=False)
    first_name: Mapped[str] = Column(String, nullable=False)
    last_name: Mapped[str] = Column(String, nullable=False)
    email: Mapped[EmailStr] = Column(String, nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True), server_default=func.timezone("UTC", func.now())
    )
