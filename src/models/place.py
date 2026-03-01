from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as pg_uuid
from sqlalchemy import String, DateTime as saDateTime
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base_class import Base


class Place(Base):
    __tablename__ = 'place'

    id: Mapped[UUID] = mapped_column(pg_uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    city: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    seats_pattern: Mapped[str] = mapped_column(String)
    changed_at: Mapped[datetime] = mapped_column(saDateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(saDateTime(timezone=True))
