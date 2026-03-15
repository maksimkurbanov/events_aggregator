import uuid
from datetime import datetime, UTC

from sqlalchemy import insert, update, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDRepository
from src.models.outbox import Outbox, OutboxStatus
from src.schemas.outbox import OutboxCreate


class OutboxCRUD(CRUDRepository):
    async def create(self, db: AsyncSession, obj_in: OutboxCreate) -> Outbox:
        data = obj_in.model_dump()
        stmt = insert(Outbox).values(**data).returning(Outbox)
        result = await db.execute(stmt)
        return result.scalars().one()

    async def mark_sent(self, db: AsyncSession, outbox_id: uuid.UUID) -> None:
        stmt = (
            update(Outbox)
            .where(Outbox.id == outbox_id)
            .values(status=OutboxStatus.SENT, updated_at=datetime.now(UTC))
        )
        await db.execute(stmt)

    async def get_pending(self, db: AsyncSession, limit: int = 100) -> list[Outbox]:
        stmt = (
            select(Outbox)
            .where(Outbox.status == OutboxStatus.PENDING)
            .order_by(Outbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


outbox_crud = OutboxCRUD(model=Outbox)
