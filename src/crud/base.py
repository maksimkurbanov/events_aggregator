from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.log import get_logger

ORMModel = TypeVar("ORMModel")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

log = get_logger(__name__)


class CRUDRepository:
    def __init__(self, model: type[ORMModel]) -> None:
        self._model = model
        self._name = model.__name__

    async def get_one(self, db: AsyncSession, *args, **kwargs) -> ORMModel | None:
        log.debug("retrieving one record for %s", self._model.__name__)
        stmt = db.select(self._model).filter(*args).filter_by(**kwargs)
        query_result = await db.execute(stmt)
        return query_result.scalars().first()

    async def get_many(self, db: AsyncSession, *args, **kwargs) -> list[ORMModel]:
        log.debug("retrieving many records for %s", self._model.__name__)
        stmt = db.select(self._model).filter(*args).filter_by(**kwargs)
        query_result = await db.execute(stmt)
        return query_result.scalars().all()

    async def create(self, db: AsyncSession, obj_create: CreateSchemaType) -> ORMModel:
        log.debug(
            "creating record for %s with data %s",
            str(self._model.__name__),
            obj_create.model_dump(),
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
            "updating record for %s with data %s",
            self._model.__name__,
            obj_update.model_dump(),
        )
        obj_update_data = obj_update.model_dump(exclude_unset=True)
        for field, value in obj_update_data.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, db_obj: ORMModel) -> None:
        log.debug("deleting record for %s with id %s", self._model.__name__, db_obj.id)
        await db.delete(db_obj)
        await db.commit()
        return db_obj
