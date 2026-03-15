from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as pg_uuid
from sqlalchemy.orm import Mapped
from sqlalchemy.testing.schema import mapped_column

from src.models.base_class import Base


class EventSeatsCache(Base):
    __tablename__ = "event_seats_cache"

    event_id: Mapped[UUID] = mapped_column(pg_uuid, primary_key=True)
    seats: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
