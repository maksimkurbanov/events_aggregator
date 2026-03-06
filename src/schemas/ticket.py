from uuid import UUID

from pydantic import BaseModel, EmailStr

from src.schemas.event import SeatStr


class TicketInDB(BaseModel):
    ticket_id: UUID
    first_name: str
    last_name: str


class BuyTicketRequest(BaseModel):
    event_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    seat: SeatStr


class BuyTicketProviderRequest(BaseModel):
    first_name: str
    last_name: str
    seat: SeatStr
    email: EmailStr


class TicketUpdate(BuyTicketRequest):
    ticket_id: UUID
