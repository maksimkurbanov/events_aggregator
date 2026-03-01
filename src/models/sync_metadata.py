from datetime import datetime

from sqlalchemy import DateTime as saDateTime
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base_class import Base


class SyncMetadata(Base):
    __tablename__ = "sync_metadata"

    sync_timestamp: Mapped[datetime] = mapped_column(
        saDateTime(timezone=True),
        server_default=func.timezone("UTC", func.now()),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    last_changed_at: Mapped[datetime] = mapped_column(saDateTime(timezone=True))
    type: Mapped[str] = mapped_column(String, nullable=True)
