from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import event_exists_and_published
from src.crud.tickets import tickets_crud
from src.database.database import get_db
from src.external.events_provider import get_events_provider_client
from src.schemas.ticket import BuyTicketProviderRequest, BuyTicketRequest, TicketUpdate
from src.utils.log import get_logger

log = get_logger(__name__)

ticket_router = APIRouter(prefix="/api", tags=["Tickets"])


@ticket_router.post("/tickets")
async def buy_ticket(
    ticket_data: BuyTicketRequest,
    client: Annotated[AsyncClient, Depends(get_events_provider_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    event = await event_exists_and_published(ticket_data.event_id, db)
    ticket_data_for_provider = BuyTicketProviderRequest.model_validate(
        ticket_data.model_dump(exclude={"event_id"})
    )
    dat = ticket_data_for_provider.model_dump()
    log.debug(f"{dat=}")
    try:
        ticket = client.register(event.id, **dat)
    except httpx.HTTPError as e:
        log.error(
            f"Ticket registration API request to Events Provider failed: {e.response.text}"
        )
        raise HTTPException(status_code=400, detail="Ticket registration failed") from e
    else:
        ticket_update_data = ticket_data.model_dump()
        ticket_update_data.update({"ticket_id": ticket["ticket_id"]})
        log.debug(f"{ticket_update_data=}")
        ticket_update_data = TicketUpdate.model_validate(ticket_update_data)
        await tickets_crud.upsert(db, ticket_update_data, "ticket_id")

        return ticket
