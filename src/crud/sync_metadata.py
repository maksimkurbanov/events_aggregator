from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDRepository
from src.models.sync_metadata import SyncMetadata


class SyncMetadataRepository(CRUDRepository):
    async def get_max_last_changed_at(self, db: AsyncSession) -> datetime | None:
        stmt = select(func.max(self._model.last_changed_at))
        result = await db.execute(stmt)
        return result.scalars().one_or_none()


sync_crud = SyncMetadataRepository(model=SyncMetadata)
