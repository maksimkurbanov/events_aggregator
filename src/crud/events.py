from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDRepository, ORMModel
from src.models.event import Event


class EventsRepository(CRUDRepository):
    async def get_many_with_count(
        self,
        db: AsyncSession,
        *args,
        order_by: str | None,
        offset: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> tuple[int, list[ORMModel]] | None:
        filtering_stmt = select(self._model).filter(*args).filter_by(**kwargs)
        count_stmt = select(func.count()).select_from(filtering_stmt.subquery())
        result = await db.execute(count_stmt)
        count = result.scalars().one_or_none()
        paginated_events = await self.get_many(
            db, *args, order_by=order_by, offset=offset, limit=limit, **kwargs
        )
        return count, paginated_events


events_crud = EventsRepository(model=Event)
