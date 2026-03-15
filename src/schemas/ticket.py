from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict

from src.schemas.event import SeatStr


class BuyTicketRequest(BaseModel):
    event_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    seat: SeatStr
    idempotency_key: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BuyTicketProviderRequest(BaseModel):
    first_name: str
    last_name: str
    seat: SeatStr
    email: EmailStr


class TicketUpdate(BuyTicketRequest):
    ticket_id: UUID

    model_config = ConfigDict(from_attributes=True)
