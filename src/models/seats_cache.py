from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as pg_uuid
from sqlalchemy.orm import Mapped

from src.models.base_class import Base


class EventSeatsCache(Base):
    __tablename__ = "event_seats_cache"

    event_id: Mapped[UUID] = Column(pg_uuid, primary_key=True)
    seats: Mapped[list[str]] = Column(ARRAY(String), nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True))
