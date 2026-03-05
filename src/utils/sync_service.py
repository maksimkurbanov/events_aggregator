from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.events import events_crud
from src.crud.sync_metadata import sync_crud
from src.database.database import get_ctx_db
from src.external.events_provider import EventsPaginator, EventsProviderClient
from src.models.sync_metadata import SyncMetadata
from src.schemas.event import EventCreate
from src.schemas.sync_metadata import SyncMetadataCreate
from src.utils.datetime_converter import str_to_dt_utc
from src.utils.log import get_logger

log = get_logger(__name__)


async def do_sync(
    sync_type: str = "scheduled", db: AsyncSession = get_ctx_db
) -> dict[str, str]:
    log.info(f"Running sync of type: {sync_type}")
    async with db() as session, EventsProviderClient() as client:
        service = SyncService(session, client)
        return await service.sync(sync_type)


class SyncService:
    def __init__(self, db: AsyncSession, client: EventsProviderClient) -> None:
        self.db = db
        self.client = client

    async def _get_last_changed_at(self) -> datetime:
        last_changed_at = await sync_crud.get_max_last_changed_at(self.db)
        if not last_changed_at:
            last_changed_at = str_to_dt_utc("2000-01-01")
        return last_changed_at

    async def _update_sync_metadata(
        self, status: str, message: str, last_changed_at: datetime, sync_type: str
    ) -> SyncMetadata:
        upd_dict = {
            "status": f"{status}: {message}",
            "last_changed_at": last_changed_at,
            "type": sync_type,
        }
        updated_model = SyncMetadataCreate.model_validate(upd_dict)
        return await sync_crud.create(self.db, updated_model)

    async def _save_events(self, events: list[dict[str, Any]]) -> None:
        event_creates = [EventCreate.model_validate(event) for event in events]
        log.debug(f"Saving {len(event_creates)} events")

        if event_creates:
            await events_crud.bulk_upsert(self.db, event_creates)

        log.info(f"Parsed {len(events)} events")

    async def sync(self, sync_type: str) -> dict[str, str]:
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
        except httpx.HTTPError as e:
            await self._update_sync_metadata(
                status="failed",
                message=str(e),
                last_changed_at=current_max,
                sync_type=sync_type,
            )
            return {"status": "failed"}
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
            return {"status": "success"}
