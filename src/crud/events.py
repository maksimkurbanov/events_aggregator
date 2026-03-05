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

    async def upsert(self, db: AsyncSession, obj_in: EventCreate) -> Event:
        """
        Insert or update an event based on its id.
        obj_in must contain all fields, including id.
        Returns the ORM object after the operation.
        """
        data = obj_in.model_dump()
        stmt = pg_insert(self._model).values(**data)
        # On conflict (=existing rows) update all columns except 'id' with new, freshly-fetched values
        update_data = {k: v for k, v in data.items() if k != "id"}
        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_data)
        await db.execute(stmt)
        await db.commit()

    async def bulk_upsert(
        self, db: AsyncSession, objs_in: list[EventCreate]
    ) -> list[Event]:
        """
        Perform a bulk upsert for multiple events.
        Returns the list of Event ORM objects after the operation.
        """
        if not objs_in:
            return []

        rows = [obj.model_dump() for obj in objs_in]
        stmt = pg_insert(self._model).values(rows)

        # On conflict (=existing rows) update all columns except 'id' with new, freshly-fetched values
        update_data = {
            col: getattr(stmt.excluded, col) for col in rows[0] if col != "id"
        }

        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_data)

        await db.execute(stmt)
        await db.commit()

        # Retrieve the full ORM objects for the affected ids
        # ids = result.scalars().all()
        # if ids:
        #     # Use the existing get_many method (or a simple select)
        #     events = await self.get_many(db, Event.id.in_(ids), order_by=None)
        #     return events
        return []


events_crud = EventsRepository(model=Event)
