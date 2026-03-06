from datetime import date, datetime
from json import JSONEncoder
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.log import get_logger

ORMModel = TypeVar("ORMModel")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

log = get_logger(__name__)


old_default = JSONEncoder.default


def new_default(self, obj):
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return old_default(self, obj)


JSONEncoder.default = new_default


class CRUDRepository:
    def __init__(self, model: type[ORMModel]) -> None:
        self._model = model
        self._name = model.__name__
        self.id_col = self._get_primary_key_col_names()

    def _get_primary_key_col_names(self):
        res = [column.name for column in inspect(self._model).primary_key]
        log.debug(f"Primary key columns in model {self._name}: {res}")
        return res

    async def get_one(self, db: AsyncSession, *args, **kwargs) -> ORMModel | None:
        log.debug(f"Retrieving one record for {self._name}")
        stmt = select(self._model).filter(*args).filter_by(**kwargs)
        query_result = await db.execute(stmt)
        obj = query_result.scalars().first()
        if obj:
            log.debug(f"Query result for get_one: {obj.__dict__}")
        return obj

    async def get_many(
        self,
        db: AsyncSession,
        *args,
        order_by: str | None,
        offset: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> list[ORMModel]:
        log.debug(f"Retrieving many records for {self._name}")
        stmt = (
            select(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(order_by)
            .offset(offset)
            .limit(limit)
        )
        query_result = await db.execute(stmt)
        return query_result.scalars().all()

    async def create(self, db: AsyncSession, obj_create: CreateSchemaType) -> ORMModel:
        log.debug(
            f"Creating record for {self._name} with data {obj_create.model_dump()}"
        )
        obj_create_data = obj_create.model_dump(exclude_unset=True, exclude_none=True)
        db_obj = self._model(**obj_create_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, db_obj: ORMModel, obj_update: UpdateSchemaType
    ) -> ORMModel:
        log.debug(
            f"Creating record for {self._name} with data {obj_update.model_dump()}"
        )
        obj_update_data = obj_update.model_dump(exclude_unset=True)
        for field, value in obj_update_data.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def upsert(self, db: AsyncSession, obj_in: UpdateSchemaType) -> ORMModel:
        """
        Insert or update an event based on its Primary Key column(s)
        obj_in must contain all fields, including all Primary Key values.
        Returns the ORM object after the operation.
        """
        data = obj_in.model_dump()
        log.debug(f"Updating record for {self._name} with data {data}")
        stmt = pg_insert(self._model).values(**data)
        # On conflict (=existing rows with same PKs) update all columns except PKs
        # with values passed in obj_in
        update_data = {k: v for k, v in data.items() if k not in self.id_col}
        stmt = stmt.on_conflict_do_update(index_elements=self.id_col, set_=update_data)
        await db.execute(stmt)
        await db.commit()

        # Get and return upserted object using it's PK(s) value(s) from session's identity map
        pk_values = tuple(data[col] for col in self.id_col)
        return await db.get(self._model, pk_values)

    async def delete(self, db: AsyncSession, db_obj: ORMModel) -> None:
        pk_values = {col: getattr(db_obj, col) for col in self.id_col}
        log.debug(f"Deleting record for {self._name} with id {pk_values}")
        await db.delete(db_obj)
        await db.commit()
        return db_obj
