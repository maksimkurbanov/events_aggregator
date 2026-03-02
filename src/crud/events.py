from src.crud.base import CRUDRepository
from src.models.event import Event

events_crud = CRUDRepository(model=Event)
