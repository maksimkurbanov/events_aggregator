from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database import get_db
from src.external.events_provider import EventsProviderClient
from src.services.event_service import EventService
from src.services.sync_service import SyncService
from src.services.ticket_service import TicketService
from src.utils.log import get_logger

log = get_logger(__name__)


async def get_event_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventService:
    """
    Dependency that returns an instance of EventService initialised with
    database session. For use by route handlers that need event-related
    business logic
    """
    return EventService(db)


async def get_ticket_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    events_service: Annotated[EventService, Depends(get_event_service)],
    provider_client: Annotated[
        EventsProviderClient, Depends(get_events_provider_client)
    ],
) -> TicketService:
    """
    Dependency that returns an instance of TicketService initialised
    with database session, EventService and EventsProviderClient instances
    """
    return TicketService(db, events_service, provider_client)


async def get_sync_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_client: Annotated[
        EventsProviderClient, Depends(get_events_provider_client)
    ],
) -> SyncService:
    """Dependency that returns an instance of SyncService initialised
    with database session, and EventsProvider client instances"""
    return SyncService(db, provider_client)


async def get_events_provider_client() -> AsyncGenerator[Any, Any]:
    """
    Dependency that yields an instance of EventsProviderClient for
    interaction with external Events Provider
    """
    async with EventsProviderClient() as client:
        yield client
