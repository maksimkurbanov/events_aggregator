from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDRepository
from src.models.sync_metadata import SyncMetadata


class SyncEventRepository(CRUDRepository):
    def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """
        Get a user by email.

        Parameters:
            db (Session): The database session.
            email (str): The email of the user.

        Returns:
            Optional[User]: The user found by email, or None if not found.
        """
        return self.get_one(db, self._model.email == email)

sync_crud = SyncEventRepository()