from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.events import events_crud
from src.database.database import get_db
from src.log import get_logger
from src.models.event import Event
from src.schemas.event import EventsRequest, EventsResponse, SingleEventResponse

log = get_logger(__name__)
events_router = APIRouter(prefix="/api", tags=["events"])


@events_router.get("/events", response_model=EventsResponse)
async def get_events(
    request: Request,
    request_query_params: Annotated[EventsRequest, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    date_from = request_query_params.date_from
    page = request_query_params.page
    page_size = request_query_params.page_size
    offset = (page - 1) * page_size
    datetime_date_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=UTC)
    count, events = await events_crud.get_many_with_count(
        db,
        Event.event_time >= datetime_date_from,
        order_by=Event.event_time,
        offset=offset,
        limit=page_size,
    )

    base_url = request.url_for("get_events")
    next_url = None
    prev_url = None

    if offset + page_size < count:
        next_url = (
            f"{base_url}?date_from={date_from}&page={page + 1}&page_size={page_size}"
        )
    if page > 1:
        prev_url = (
            f"{base_url}?date_from={date_from}&page={page - 1}&page_size={page_size}"
        )

    return EventsResponse(
        count=count,
        next=next_url,
        previous=prev_url,
        results=[SingleEventResponse.model_validate(event) for event in events],
    )
