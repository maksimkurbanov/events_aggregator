from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDRepository, ORMModel
from src.models.event import Event
from src.schemas.event import EventCreate
from src.utils.log import get_logger

log = get_logger(__name__)


class EventsRepository(CRUDRepository):
    async def get_many_with_count(
        self,
        db: AsyncSession,
        *args,
        order_by: str | None,
        offset: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> tuple[int | None, list[ORMModel]]:
        filtering_stmt = select(self._model).filter(*args).filter_by(**kwargs)
        count_stmt = select(func.count()).select_from(filtering_stmt.subquery())
        result = await db.execute(count_stmt)
        count = result.scalars().one_or_none()
        paginated_events = await self.get_many(
            db, *args, order_by=order_by, offset=offset, limit=limit, **kwargs
        )
        return count, paginated_events

    async def bulk_upsert(
        self, db: AsyncSession, objs_in: list[EventCreate]
    ) -> list[dict]:
        """
        Perform a bulk upsert for multiple events, based on their
        Primary Key columns (works for composite PKs as well).
        objs_in must contain all fields, including all Primary Key values.
        Returns the list of Event ORM objects after the operation.
        """
        if not objs_in:
            return []

        rows = [obj.model_dump() for obj in objs_in]

        # Get the table object to access columns
        table = self._model.__table__
        # Convert primary key column names to actual column objects
        pk_columns = [table.c[col_name] for col_name in self.id_col]

        stmt = pg_insert(self._model).values(rows)

        # On conflict (=existing rows) update all columns except 'id' with new, freshly-fetched values
        update_data = {
            col: getattr(stmt.excluded, col)
            for col in rows[0]
            if col not in self.id_col
        }
        # Return PKs only, instead of complete ORM representations, for brevity
        stmt = stmt.on_conflict_do_update(
            index_elements=self.id_col, set_=update_data
        ).returning(*pk_columns)

        result = await db.execute(stmt)
        await db.commit()

        # Convert rows to list of dictionaries (formed from (column, value) tuples)
        return [dict(zip(self.id_col, row)) for row in result.all()]


events_crud = EventsRepository(model=Event)
