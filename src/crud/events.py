from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDRepository, ORMModel
from src.models.event import Event
from src.schemas.event import EventCreate
from src.utils.log import get_logger

log = get_logger(__name__)


class EventsRepository(CRUDRepository):
    """CRUD interface for Event model"""

    async def get_many_with_count(
        self,
        db: AsyncSession,
        *args,
        order_by: str | None,
        offset: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> tuple[int, list[ORMModel]]:
        """
        Fetch all records satisfying provided args and kwargs filtering,
        store number of hits in 'count' variable
        Respects given offset and limit.
        Return a tuple of count and events
        """
        filtering_stmt = select(self._model).filter(*args).filter_by(**kwargs)
        count_stmt = select(func.count()).select_from(filtering_stmt.subquery())
        result = await db.execute(count_stmt)
        count = result.scalars().one_or_none()
        events = await self.get_many(
            db, *args, order_by=order_by, offset=offset, limit=limit, **kwargs
        )
        return count, events

    async def bulk_upsert(
        self, db: AsyncSession, objs_in: list[EventCreate]
    ) -> list[dict]:
        """
        Perform a bulk upsert for multiple events, based on their
        Primary Key columns (works for composite PKs as well).
        On conflict (existing row with same Primary Key) update all
        columns of a record except Primary Key with values passed in objs_in.
        objs_in must contain all fields, including all Primary Key values.
        Return list of dicts containing pk_column:pk_value pairs,
        representing updated rows (not full ORMModels, for brevity's sake).
        """
        rows = [obj.model_dump() for obj in objs_in]
        table = self._model.__table__
        pk_columns = [table.c[col_name] for col_name in self.id_cols]

        stmt = pg_insert(self._model).values(rows)
        update_data = {
            col: getattr(stmt.excluded, col)
            for col in rows[0]
            if col not in self.id_cols
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=self.id_cols, set_=update_data
        ).returning(*pk_columns)
        result = await db.execute(stmt)

        return [dict(zip(self.id_cols, row)) for row in result.all()]


events_crud = EventsRepository(model=Event)
