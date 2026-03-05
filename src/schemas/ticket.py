from uuid import UUID

from pydantic import BaseModel
from pydantic.v1 import EmailStr

from src.schemas.event import SeatStr


class BuyTicket(BaseModel):
    event_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    seat: SeatStr
