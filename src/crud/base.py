from datetime import date, datetime
from json import JSONEncoder
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
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

    async def get_one(self, db: AsyncSession, *args, **kwargs) -> ORMModel | None:
        log.debug(f"Retrieving one record for {self._name}")
        stmt = select(self._model).filter(*args).filter_by(**kwargs)
        query_result = await db.execute(stmt)
        obj = query_result.scalars().first()
        log.debug(f"Query result for get_one: {obj}")
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

    async def delete(self, db: AsyncSession, db_obj: ORMModel) -> None:
        log.debug(f"Deleting record for {self._name} with id {db_obj.id}")
        await db.delete(db_obj)
        await db.commit()
        return db_obj
