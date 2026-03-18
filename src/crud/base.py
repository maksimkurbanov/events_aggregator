from datetime import date, datetime
from json import JSONEncoder
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import inspect, select, update
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
    """Base interface for CRUD operations"""

    def __init__(self, model: type[ORMModel]) -> None:
        """
        Initialize the CRUD repository.

        Parameters:
            model (Type[ORMModel]): The ORM model to use for CRUD operations
        """
        self._model = model
        self._name = model.__name__
        self.id_cols = self._get_primary_key_cols()

    def _get_primary_key_cols(self) -> list[str]:
        """Create and return a list of Primary Key SQL Alchemy Column objects"""
        pk_list = [column.name for column in inspect(self._model).primary_key]
        log.debug(f"Primary key columns in model {self._name}: {pk_list}")
        return pk_list

    async def get_one(self, db: AsyncSession, *args, **kwargs) -> ORMModel | None:
        """
        Fetch one record satisfying provided args and kwargs filtering.
        Return ORMModel or None
        """
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
        order_by: str | None = None,
        offset: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> list[ORMModel]:
        """
        Fetch all records satisfying provided args and kwargs filtering.
        Respects given offset and limit.
        Return list of ORMModel objects or an empty list
        """
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

    async def get_many_with_lock(
        self,
        db: AsyncSession,
        *args,
        order_by: str | None = None,
        offset: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> list[ORMModel]:
        """
        Fetch all records satisfying provided args and kwargs filtering,
        with exclusive lock on selected rows, while skipping already
        locked rows, to ensure data integrity in concurrent environment.
        Respects given offset and limit.
        Return list of ORMModel objects or an empty list
        """
        stmt = (
            select(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(order_by)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_create: CreateSchemaType) -> ORMModel:
        """ "
        Create a new record in the database
        Return created ORMModel object
        """
        log.debug(
            f"Creating record for {self._name} with data {obj_create.model_dump()}"
        )
        obj_create_data = obj_create.model_dump(exclude_unset=True)
        stmt = pg_insert(self._model).values(**obj_create_data).returning(self._model)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def update(
        self, db: AsyncSession, db_obj: ORMModel, obj_update: UpdateSchemaType
    ) -> ORMModel:
        """
        Update an existing record in the database
        Return updated ORMModel object
        """
        obj_update_data = obj_update.model_dump(exclude_unset=True)

        pk_values, target_ids = {}, []

        for col in self.id_cols:
            pk_values[col] = getattr(db_obj, col)
            target_ids.append(getattr(self._model, col) == getattr(db_obj, col))

        log.debug(
            f"Updating {self._name} record with Primary Key(s): {pk_values} with data: {obj_update_data}"
        )

        stmt = (
            update(self._model)
            .filter(*target_ids)
            .values(**obj_update_data)
            .returning(self._model)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def upsert(self, db: AsyncSession, obj_in: UpdateSchemaType) -> ORMModel:
        """
        Create a new record in database, on conflict (existing row with same
        Primary Key) update all columns of a record except Primary Key with
        values passed in obj_in. obj_in must contain all fields, including
        all Primary Key values.
        Argument 'commit' can be set to False to bundle upsert() in the same
        transaction with other operations.
        Return new or updated ORMModel object
        """
        data = obj_in.model_dump()
        log.debug(f"Updating record for {self._name} with data {data}")
        stmt = pg_insert(self._model).values(**data)
        update_data = {k: v for k, v in data.items() if k not in self.id_cols}
        stmt = stmt.on_conflict_do_update(index_elements=self.id_cols, set_=update_data)
        await db.execute(stmt)
        pk_values = tuple(data[col] for col in self.id_cols)
        return await db.get(self._model, pk_values)

    async def delete(self, db: AsyncSession, db_obj: ORMModel) -> None:
        """
        Delete an existing record from the database
        Return None
        """
        pk_values = {col: getattr(db_obj, col) for col in self.id_cols}
        log.debug(f"Deleting record for {self._name} with id {pk_values}")
        await db.delete(db_obj)
        return None
