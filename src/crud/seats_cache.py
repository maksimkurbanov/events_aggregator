from src.crud.base import CRUDRepository
from src.models.seats_cache import EventSeatsCache

seats_cache_crud = CRUDRepository(model=EventSeatsCache)
