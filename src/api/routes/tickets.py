from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import event_exists, event_exists_and_published, validate_seat
from src.crud.tickets import tickets_crud
from src.database.database import get_db
from src.external.events_provider import get_events_provider_client
from src.models.ticket import Ticket
from src.schemas.ticket import BuyTicketProviderRequest, BuyTicketRequest, TicketUpdate
from src.utils.log import get_logger

log = get_logger(__name__)

ticket_router = APIRouter(prefix="/api", tags=["Tickets"])


@ticket_router.post("/tickets")
async def buy_ticket(
    ticket_data: BuyTicketRequest,
    client: Annotated[AsyncClient, Depends(get_events_provider_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
):
    event = await event_exists_and_published(ticket_data.event_id, db)
    if datetime.now(UTC) >= event.registration_deadline:
        raise HTTPException(
            status_code=403, detail="Cannot register past registration deadline"
        )
    if not validate_seat(ticket_data.seat, event.place["seats_pattern"]):
        raise HTTPException(status_code=403, detail="Invalid seat")
    ticket_data_for_provider = BuyTicketProviderRequest.model_validate(
        ticket_data.model_dump(exclude={"event_id"})
    )
    ticket_data_for_provider = ticket_data_for_provider.model_dump()
    try:
        ticket = client.register(event.id, **ticket_data_for_provider)
        response.status_code = status.HTTP_201_CREATED
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail="Ticket registration failed") from e
    else:
        ticket_update_data = ticket_data.model_dump()
        # Inject data to comply with TicketUpdate schema
        ticket_update_data.update(ticket)
        ticket_update_data = TicketUpdate.model_validate(ticket_update_data)
        await tickets_crud.upsert(db, ticket_update_data)
        return ticket


@ticket_router.delete("/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: UUID,
    client: Annotated[AsyncClient, Depends(get_events_provider_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ticket = await tickets_crud.get_one(db, Ticket.ticket_id == ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=404, detail=f"Ticket with ID {ticket_id} not found"
        )
    event = await event_exists(ticket.event_id, db)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.event_time < datetime.now(UTC):
        raise HTTPException(
            status_code=403, detail="Cannot cancel: The event has already taken place"
        )
    response = await client.unregister(event.id, ticket_id=ticket.ticket_id)
    if response["success"] == True:
        await tickets_crud.delete(db, ticket)
        return {"success": True}
