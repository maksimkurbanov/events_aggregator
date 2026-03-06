from src.crud.base import CRUDRepository
from src.models.ticket import Ticket

tickets_crud = CRUDRepository(model=Ticket)
