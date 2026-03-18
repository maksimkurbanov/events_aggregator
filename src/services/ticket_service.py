from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from src.api.routes.exceptions import (
    EntityNotFoundError,
    EntityBadDataError,
    OperationFailedError,
)
from src.crud.outbox import outbox_crud
from src.crud.tickets import tickets_crud
from src.external.events_provider import EventsProviderClient
from src.models.ticket import Ticket
from src.schemas.outbox import OutboxCreate
from src.schemas.ticket import (
    BuyTicketProviderRequest,
    TicketUpdate,
    BuyTicketRequest,
    TicketResponse,
)
from src.services.event_service import EventService
from datetime import UTC, datetime

from src.utils.create_lock_key import create_lock_key
from src.utils.log import get_logger

log = get_logger(__name__)


class TicketService:
    """Interface for buying and cancelling tickets"""

    def __init__(
        self, db: AsyncSession, events: EventService, client: EventsProviderClient
    ):
        self.db = db
        self.events = events
        self.client = client

    def _validate_seat(self, seat: str, seat_pattern: str) -> bool:
        """Determine if a seat belongs to the given seat pattern"""
        seat_letter, seat_number = seat[0], int(seat[1:])

        for pattern in seat_pattern.split(","):
            if seat_letter == pattern[0]:
                pattern_start, pattern_end = map(int, pattern[1:].split("-"))
                if seat_number in range(pattern_start, pattern_end + 1):
                    return True
        return False

    async def _acquire_idempotency_lock(self, key: str) -> None:
        """Acquire a transaction‑scoped advisory lock for the given key"""
        lock_id = create_lock_key(key)
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id}
        )

    async def _validate_idempotency(self, data: dict) -> TicketResponse | None:
        """
        Determine if provided data completely matches entry in DB with
        same idempotency_key
        Return None if there is any mismatch between data and DB entry,
        return TicketResponse otherwise
        """
        existing_ticket = await tickets_crud.get_one(
            self.db, Ticket.idempotency_key == data["idempotency_key"]
        )
        if existing_ticket:
            data_in_db = BuyTicketRequest.model_validate(existing_ticket).model_dump()
            if data_in_db != data:
                raise TicketBadIdempotencyKeyError(
                    "Idempotency key does not match data"
                )
            return TicketResponse(ticket_id=existing_ticket.ticket_id)
        return None

    def _gen_outbox_payload(
        self, event_name: str, ticket_id: UUID, idempotency_key: str | None = None
    ) -> dict:
        """Generate data for outbox event's payload column"""
        return {
            "message": f"Вы успешно зарегистрированы на мероприятие - {event_name}",
            "reference_id": str(ticket_id),
            "idempotency_key": idempotency_key,
        }

    async def buy_ticket(self, ticket_data: dict) -> dict[str, Any]:
        """
        Business logic to buy ticket

        Checks constraints:
        - Valid idempotency key (if provided in request)
        - Event exists and is published
        - Current time isn't past event registration deadline
        - Requested seat complies with event's place seat pattern
          (i.e. seat A50 is okay for A1-500 pattern, seat A600 is not)
        - Requested seat is currently available

        Return dict with ticket_id
        """
        log.debug(f"buy_ticket {ticket_data=}")
        idempotency_key = ticket_data.get("idempotency_key", None)
        if idempotency_key:
            await self._acquire_idempotency_lock(idempotency_key)
            correct_ticket = await self._validate_idempotency(ticket_data)
            if correct_ticket:
                return correct_ticket

        event = await self.events.verified_event(
            ticket_data["event_id"], check_published=True
        )
        if datetime.now(UTC) >= event.registration_deadline:
            raise TicketBadDataError("Cannot register past registration deadline")
        if not self._validate_seat(ticket_data["seat"], event.place["seats_pattern"]):
            raise TicketBadDataError(f"Invalid seat: {ticket_data['seat']}")
        seats = await self.events.get_seats(ticket_data["event_id"], self.client)
        if ticket_data["seat"] not in seats.available_seats:
            raise TicketBadDataError(f"Seat is unavailable: {ticket_data['seat']}")

        ticket_data_for_provider = BuyTicketProviderRequest.model_validate(
            ticket_data
        ).model_dump(exclude={"event_id"})
        try:
            ticket = await self.client.register(
                ticket_data["event_id"], **ticket_data_for_provider
            )
        except httpx.HTTPError:
            raise TicketRegistrationFailedError("Ticket registration failed")

        ticket_data.update(ticket)
        ticket_update_data = TicketUpdate.model_validate(ticket_data)
        await tickets_crud.create(self.db, ticket_update_data)

        outbox_payload = self._gen_outbox_payload(
            event.name, ticket_data["ticket_id"], idempotency_key
        )
        outbox_entry = OutboxCreate(
            event_type="ticket_purchased", payload=outbox_payload
        )
        await outbox_crud.create(self.db, outbox_entry)
        await self.db.commit()
        return ticket

    async def delete_ticket(self, ticket_id: UUID) -> JSONResponse:
        """
        Delete record with given ticket_id from database
        Return JSONResponse
        """
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
            await self.db.commit()
            return JSONResponse(status_code=200, content={"success": True})


class TicketNotFoundError(EntityNotFoundError):
    """Raised when ticket is not found in database"""

    pass


class TicketBadDataError(EntityBadDataError):
    """Raised when provided ticket data does not match constraints"""

    pass


class TicketBadIdempotencyKeyError(EntityBadDataError):
    """
    Raised when idempotency key and data in request do not
    match idempotency key and data in database
    """

    status_code = 409


class TicketRegistrationFailedError(OperationFailedError):
    """Raised when the external provider ticket registration fails"""

    pass


class TicketCancellationFailedError(OperationFailedError):
    """Raised when the external provider ticket cancellation fails"""

    pass
