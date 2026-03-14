from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.tickets import tickets_crud
from src.external.events_provider import EventsProviderClient
from src.models.ticket import Ticket
from src.schemas.ticket import BuyTicketProviderRequest, TicketUpdate
from src.services.event_service import EventService
from datetime import UTC, datetime

from src.utils.log import get_logger

log = get_logger(__name__)


class TicketService:
    def __init__(
        self, db: AsyncSession, events: EventService, client: EventsProviderClient
    ):
        self.db = db
        self.events = events
        self.client = client

    def _validate_seat(self, seat: str, seat_pattern: str) -> bool:
        seat_letter, seat_number = seat[0], int(seat[1:])

        for pattern in seat_pattern.split(","):
            if seat_letter == pattern[0]:
                pattern_start, pattern_end = map(int, pattern[1:].split("-"))
                if seat_number in range(pattern_start, pattern_end + 1):
                    return True
        return False

    async def buy_ticket(self, ticket_data: dict):
        event = await self.events.verified_event(
            ticket_data["event_id"], check_published=True
        )
        if datetime.now(UTC) >= event.registration_deadline:
            raise TicketBadDataError("Cannot register past registration deadline")
        if not self._validate_seat(ticket_data["seat"], event.place["seats_pattern"]):
            raise TicketBadDataError(f"Invalid seat: {ticket_data['seat']}")

        ticket_data_for_provider = BuyTicketProviderRequest.model_validate(ticket_data)
        ticket_data_for_provider = ticket_data_for_provider.model_dump(
            exclude={"event_id"}
        )
        try:
            ticket = await self.client.register(event.id, **ticket_data_for_provider)
        except httpx.HTTPError:
            raise TicketRegistrationFailedError("Ticket registration failed")
        else:
            ticket_data.update(ticket)
            ticket_update_data = TicketUpdate.model_validate(ticket_data)
            await tickets_crud.upsert(self.db, ticket_update_data)
            return ticket

    async def delete_ticket(self, ticket_id: UUID):
        ticket = await tickets_crud.get_one(self.db, Ticket.ticket_id == ticket_id)
        if not ticket:
            raise TicketNotFoundError(f"Ticket with ID {ticket_id} not found")
        event = await self.events.get_single_event(ticket.event_id)
        if event.event_time < datetime.now(UTC):
            raise TicketBadDataError("Cannot cancel: event has already taken place")

        try:
            await self.client.unregister(event.id, ticket_id=ticket.ticket_id)
        except httpx.HTTPError:
            raise TicketCancellationFailedError("Failed to cancel ticket")
        else:
            await tickets_crud.delete(self.db, ticket)
            return {"success": True}


class TicketBadDataError(Exception):
    """Raised when an event cannot be found"""

    pass


class TicketRegistrationFailedError(Exception):
    """Raised when the external provider ticket registration fails"""

    pass


class TicketNotFoundError(Exception):
    """Raised when ticket is not found in local DB"""

    pass


class TicketCancellationFailedError(Exception):
    """Raised when the external provider ticket registration fails"""

    pass
