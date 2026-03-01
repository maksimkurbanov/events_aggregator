from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Integer, String
from sqlalchemy import DateTime as saDateTime
from sqlalchemy.dialects.postgresql import UUID as pg_uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base_class import Base


class Event(Base):
    __tablename__ = "event"

    id: Mapped[UUID] = mapped_column(pg_uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    # place_id: Mapped[UUID] = mapped_column(pg_uuid, ForeignKey('place.id'))
    place: Mapped[dict[str, Any]] = mapped_column(JSON)
    event_time: Mapped[datetime] = mapped_column(saDateTime(timezone=True))
    registration_deadline: Mapped[datetime] = mapped_column(saDateTime(timezone=True))
    status: Mapped[str] = mapped_column(String)
    number_of_visitors: Mapped[int] = mapped_column(Integer)
    changed_at: Mapped[datetime] = mapped_column(saDateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(saDateTime(timezone=True))
    status_changed_at: Mapped[datetime] = mapped_column(saDateTime(timezone=True))

    # place: Mapped[Place] = relationship("Place", back_populates="event")
