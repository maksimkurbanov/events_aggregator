from sqlalchemy import func, String, Text, DateTime as saDateTime
from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column

from src.models.base_class import Base


class SyncMetadata(Base):
    __tablename__ = 'sync_metadata'

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        saDateTime(timezone=True),
        server_default=func.timezone('UTC', func.now()),
        onupdate=func.timezone('UTC', func.now()),
    )
