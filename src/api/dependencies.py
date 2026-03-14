from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database import get_db
from src.external.events_provider import EventsProviderClient
from src.services.event_service import EventService
from src.services.ticket_service import TicketService


async def get_event_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventService:
    return EventService(db)


async def get_ticket_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    events_service: Annotated[EventService, Depends(get_event_service)],
    provider_client: Annotated[
        EventsProviderClient, Depends(get_events_provider_client)
    ],
) -> TicketService:
    return TicketService(db, events_service, provider_client)


async def get_events_provider_client() -> AsyncGenerator[Any, Any]:
    async with EventsProviderClient() as client:
        yield client
