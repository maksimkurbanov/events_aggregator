from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.events import events_crud
from src.database.database import get_db
from src.log import get_logger
from src.models.event import Event
from src.schemas.event import EventsResponse

log = get_logger(__name__)
events_router = APIRouter(prefix="/api", tags=["events"])


@events_router.get("/events", response_model=EventsResponse)
async def get_events(
    date_from: str = "2000-01-01",
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    datetime_date_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=UTC)
    return await events_crud.get_many(db, Event.event_time >= datetime_date_from)
