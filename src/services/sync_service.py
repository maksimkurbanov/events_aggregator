from datetime import datetime
from typing import Any, AsyncGenerator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import text
from starlette.responses import JSONResponse

from src.api.routes.exceptions import OperationFailedError
from src.crud.events import events_crud
from src.crud.sync_metadata import sync_crud
from src.database.database import engine
from src.external.events_provider import EventsProviderClient
from src.models.sync_metadata import SyncMetadata
from src.schemas.event import EventCreate
from src.schemas.sync_metadata import SyncMetadataCreate
from src.utils.create_lock_key import create_lock_key
from src.utils.datetime_converter import str_to_dt_utc
from src.utils.log import get_logger

log = get_logger(__name__)


class SyncService:
    """
    Interface for syncing events data in DB based on response from
    external Events Provider API
    """

    def __init__(self, db: AsyncSession, client: EventsProviderClient) -> None:
        self.db = db
        self.client = client

    async def _get_last_changed_at(self) -> datetime:
        """
        Fetch and return maximum value of last_changed_at column in
        SyncMetadata table
        Return timezone-aware datetime object
        """
        last_changed_at = await sync_crud.get_max_last_changed_at(self.db)
        if not last_changed_at:
            last_changed_at = str_to_dt_utc("2000-01-01")
        return last_changed_at

    async def _update_sync_metadata(
        self, status: str, message: str, last_changed_at: datetime, sync_type: str
    ) -> SyncMetadata:
        """
        Create new record in sync_metadata table
        Return SyncMetadata ORMModel object
        """
        upd_dict = {
            "status": f"{status}: {message}",
            "last_changed_at": last_changed_at,
            "type": sync_type,
        }
        updated_model = SyncMetadataCreate.model_validate(upd_dict)
        return await sync_crud.create(self.db, updated_model)

    async def _save_events(self, events: list[dict[str, Any]]) -> list[dict]:
        """
        Upsert records in event table
        Return list of dicts containing pk_column:pk_value pairs,
        representing updated rows (not full ORMModels, for brevity's sake).
        """
        event_creates = [EventCreate.model_validate(event) for event in events]
        log.debug(f"Parsed {len(events)} events")
        return await events_crud.bulk_upsert(self.db, event_creates)

    async def sync(self, sync_type: str) -> JSONResponse:
        """
        Sync all events created or updated in Events Provider since last sync
        Return JSONResponse
        """
        log.info(f"Running sync of type: {sync_type}")
        last_changed_at = await self._get_last_changed_at()
        log.info(f"Currently saved last_changed_at: {last_changed_at}")
        paginator = EventsPaginator(self.client, last_changed_at)
        current_max = last_changed_at
        total_saved = 0

        try:
            async for events in paginator:
                await self._save_events(events)
                total_saved += len(events)
                current_max = max(current_max, paginator.page_max)
        except httpx.HTTPStatusError as e:
            await self._update_sync_metadata(
                status="failed",
                message=e.response.text,
                last_changed_at=current_max,
                sync_type=sync_type,
            )
            await self.db.commit()
            raise EventsSyncFailedError("Events sync failed")
        else:
            await self._update_sync_metadata(
                status="success",
                message=f"Events synced: {total_saved}",
                last_changed_at=current_max,
                sync_type=sync_type,
            )
            if current_max > last_changed_at:
                log.info(f"last_changed_at updated to {current_max}")
            else:
                log.info("No new events since last sync")
            log.info(f"Sync complete, events parsed: {total_saved}")
            await self.db.commit()
            return JSONResponse(status_code=200, content={"status": "success"})

    async def do_sync_with_lock(self, sync_type: str = "scheduled") -> JSONResponse:
        """
        Wrapper for sync function that acquires a PostgreSQL advisory lock
        before running the actual sync. Ensures only one sync job is ran at
        a time, even across multiple processes
        """
        lock_key = create_lock_key("events_sync")

        async with engine.connect() as lock_conn:
            result = await lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key}
            )
            lock_acquired = result.scalar()

            if not lock_acquired:
                log.info("Events sync is already running elsewhere, skipping")
                return

            try:
                return await self.sync(sync_type)
            finally:
                await lock_conn.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key}
                )


class EventsPaginator:
    """Iterator for fetching events from Events Provider API"""

    def __init__(
        self,
        client: EventsProviderClient,
        last_changed_at: datetime | None = None,
    ) -> None:
        self.client = client
        self.last_changed_at = last_changed_at
        self.next_url: str | None = None
        self.page_max: datetime | None = None
        self._has_more: bool = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._has_more:
            raise StopAsyncIteration

        data = await self.client.get_events(self.last_changed_at, self.next_url)
        events = data.get("results", [])

        if not events:
            raise StopAsyncIteration

        self.page_max = max(datetime.fromisoformat(e["changed_at"]) for e in events)
        self.next_url = data.get("next", "")
        if not self.next_url:
            self._has_more = False

        return events


async def do_sync(sync_type: str, db: AsyncGenerator[AsyncSession]) -> JSONResponse:
    """
    Sync function for APScheduler job manager
    Return simple JSON on successful run
    """
    async with db() as session, EventsProviderClient() as client:
        service = SyncService(session, client)
        return await service.do_sync_with_lock(sync_type)


class EventsSyncFailedError(OperationFailedError):
    """Raised when events sync fails"""

    status_code = 502
