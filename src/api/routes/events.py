from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import (
    get_event_service,
    get_events_provider_client,
)
from src.external.events_provider import (
    EventsProviderClient,
)
from src.schemas.event import (
    EventSeatsResponse,
    PaginatedEventsRequest,
    PaginatedEventsResponse,
    SingleEventResponse,
)
from src.services.event_service import EventService
from src.utils.log import get_logger

log = get_logger(__name__)
events_router = APIRouter(prefix="/api", tags=["Events"])


@events_router.get("/events", response_model=PaginatedEventsResponse)
async def get_events(
    request: Request,
    query_params: Annotated[PaginatedEventsRequest, Depends()],
    service: Annotated[EventService, Depends(get_event_service)],
):
    return await service.get_events(
        query_params.date_from,
        query_params.page,
        query_params.page_size,
        str(request.url_for("get_events")),
        dict(request.query_params),
    )


@events_router.get("/events/{event_id}", response_model=SingleEventResponse)
async def get_single_event(
    event_id: UUID, service: Annotated[EventService, Depends(get_event_service)]
):
    return await service.get_single_event(event_id)


@events_router.get("/events/{event_id}/seats", response_model=EventSeatsResponse)
async def get_seats(
    event_id: UUID,
    client: Annotated[EventsProviderClient, Depends(get_events_provider_client)],
    service: Annotated[EventService, Depends(get_event_service)],
):
    return await service.get_seats(event_id, client)
