from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.exceptions import EntityNotFoundError, EntityBadDataError
from src.crud.events import events_crud
from src.crud.seats_cache import seats_cache_crud
from src.external.events_provider import EventsProviderClient
from src.models.event import Event
from src.models.seats_cache import EventSeatsCache
from src.schemas.event import (
    PaginatedEventsResponse,
    PaginatedEventResponse,
    EventSeatsCacheUpdate,
    EventSeatsResponse,
    SingleEventResponse,
)
from src.utils.datetime_converter import str_to_dt_utc
from src.utils.log import get_logger

log = get_logger(__name__)


class EventService:
    """Interface for handling events-related functionality"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _build_full_url(self, base_url: str, query_params: dict) -> str:
        """
        Build complete URL string with trailing slash and query parameters
        """
        if not base_url.endswith("/"):
            base_url = base_url + "/"
        # If 'page' isnt already present in query params, inject 'page=1' for correct pagination
        query_params.setdefault("page", 1)
        query_params_str = "?" + "&".join(f"{k}={v}" for k, v in query_params.items())
        return base_url + query_params_str

    async def verified_event(self, event_id: UUID, check_published: bool) -> Event:
        """
        Retrieve an event by ID and verify it exists,
        also optionally verify if it is published.
        Raises 404 if not found, 403 if not published.
        Return verified Event object
        """
        event = await events_crud.get_one(self.db, Event.id == event_id)
        if not event:
            raise EventNotFoundError(f"Event with ID {event_id} not found")
        if check_published and event.status != "published":
            raise EventNotPublishedError(f"Event with ID {event_id} not published")
        return event

    async def get_events(
        self, date_from: str, page: int, page_size: int, url: str, query_params: dict
    ) -> PaginatedEventsResponse:
        """
        Fetch events from database that match provided filters
        Return PaginatedEventsResponse
        """
        date_from = str_to_dt_utc(date_from)
        offset = (page - 1) * page_size

        count, events = await events_crud.get_many_with_count(
            self.db,
            Event.event_time >= date_from,
            order_by=Event.event_time,
            offset=offset,
            limit=page_size,
        )

        base_url_with_page = self._build_full_url(url, query_params)
        next_url = prev_url = None

        if offset + page_size < count:
            next_url = base_url_with_page.replace(f"page={page}", f"page={page + 1}")

        if page > 1:
            prev_url = base_url_with_page.replace(f"page={page}", f"page={page - 1}")

        return PaginatedEventsResponse(
            count=count,
            next=next_url,
            previous=prev_url,
            results=[PaginatedEventResponse.model_validate(event) for event in events],
        )

    async def get_single_event(self, event_id) -> SingleEventResponse:
        """Fetch single event from database based on event_id"""
        return await self.verified_event(event_id, False)

    async def get_seats(
        self, event_id, client: EventsProviderClient, use_cache: bool = True
    ) -> EventSeatsResponse:
        """
        Fetch available seats for an event:
        if no cache exists in database for this event - request valid list
        of seats from Events Provider API, otherwise use cache entry to
        form response
        Return EventSeatsResponse
        """
        event = await self.verified_event(event_id, True)
        seats = None
        if use_cache:
            seats = await seats_cache_crud.get_one(
                self.db,
                EventSeatsCache.event_id == event.id,
                EventSeatsCache.updated_at >= datetime.now(UTC) - timedelta(seconds=30),
            )
        if not seats:
            data_from_provider = await client.get_seats(event.id)
            data_from_provider.update({
                "event_id": event_id,
                "updated_at": datetime.now(UTC),
            })
            seats = EventSeatsCacheUpdate.model_validate(data_from_provider)
            await seats_cache_crud.upsert(self.db, seats)
            await self.db.commit()

        return EventSeatsResponse(event_id=seats.event_id, available_seats=seats.seats)


class EventNotFoundError(EntityNotFoundError):
    """Raised when event is not found in database"""

    pass


class EventNotPublishedError(EntityBadDataError):
    """Raised when event is not published"""

    pass
