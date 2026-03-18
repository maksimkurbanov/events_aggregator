from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict, Field

from src.schemas.event import SeatStr


class BuyTicketRequest(BaseModel):
    event_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    seat: SeatStr
    idempotency_key: str | None = Field(max_length=20, default=None)

    model_config = ConfigDict(from_attributes=True)


class BuyTicketProviderRequest(BaseModel):
    first_name: str
    last_name: str
    seat: SeatStr
    email: EmailStr


class TicketUpdate(BuyTicketRequest):
    ticket_id: UUID

    model_config = ConfigDict(from_attributes=True)


class TicketResponse(BaseModel):
    ticket_id: UUID
