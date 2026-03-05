from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.events import events_crud
from src.database.database import get_db
from src.external.events_provider import EventsProviderClient
from src.models.event import Event
from src.schemas.event import (
    EventSeatsFromProvider,
    EventSeatsResponse,
    PaginatedEventResponse,
    PaginatedEventsRequest,
    PaginatedEventsResponse,
    SingleEventResponse,
)
from src.utils.datetime_converter import str_to_dt_utc
from src.utils.log import get_logger

log = get_logger(__name__)
events_router = APIRouter(prefix="/api", tags=["Events"])


@events_router.get("/events", response_model=PaginatedEventsResponse)
async def get_events(
    request: Request,
    query_params: Annotated[PaginatedEventsRequest, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    date_from = str_to_dt_utc(query_params.date_from)
    page = query_params.page
    page_size = query_params.page_size
    offset = (page - 1) * page_size

    count, events = await events_crud.get_many_with_count(
        db,
        Event.event_time >= date_from,
        order_by=Event.event_time,
        offset=offset,
        limit=page_size,
    )

    req_url = request.url_for("get_events")
    query_p = request.query_params

    # If 'page' isnt already present in query params, inject 'page=1' for correct pagination
    query_p._dict.setdefault("page", 1)
    base_url_with_page = req_url.include_query_params(**query_p)
    next_url, prev_url = None, None

    if offset + page_size < count:
        next_url = str(base_url_with_page).replace(f"page={page}", f"page={page + 1}")

    if page > 1:
        prev_url = str(base_url_with_page).replace(f"page={page}", f"page={page - 1}")

    return PaginatedEventsResponse(
        count=count,
        next=next_url,
        previous=prev_url,
        results=[PaginatedEventResponse.model_validate(event) for event in events],
    )


@events_router.get("/events/{event_id}", response_model=SingleEventResponse)
async def get_single_event(
    event_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    event = await events_crud.get_one(db, Event.id == event_id)
    if not event:
        raise HTTPException(
            status_code=404, detail=f"Event with ID {event_id} not found"
        )
    return event


@events_router.get("/events/{event_id}/seats", response_model=EventSeatsResponse)
async def get_seats(
    event_id: UUID,
    client: Annotated[AsyncClient, Depends(EventsProviderClient)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    event = await events_crud.get_one(db, Event.id == event_id)
    if not event:
        raise HTTPException(
            status_code=404, detail=f"Event with ID {event_id} not found"
        )
    if event.status != "published":
        raise HTTPException(
            status_code=403, detail=f"Event with ID {event_id} not published"
        )
    resp = await client.get_seats(event.id)
    resp_validated = EventSeatsFromProvider.model_validate(resp)
    return {"id": event.id, "available_seats": resp_validated.seats}
