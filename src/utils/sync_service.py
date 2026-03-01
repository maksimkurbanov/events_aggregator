from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import dev_settings
from src.database.database import get_ctx_db
from src.log import get_logger
from src.models.event import Event
from src.models.sync_metadata import SyncMetadata

log = get_logger(__name__)


async def do_sync(sync_type: str = "scheduled", db: AsyncSession = get_ctx_db) -> None:
    log.info(f"Running sync of type: {sync_type}")
    async with db() as session:
        service = SyncService(session)
        await service.sync(sync_type)


class SyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.api_url = dev_settings.EVENT_PROVIDER_URL + "api/events/"
        self.api_token = dev_settings.LMS_API_KEY

    async def _get_last_changed_at(self) -> datetime:
        stmt = select(func.max(SyncMetadata.last_changed_at))
        result = await self.db.execute(stmt)
        last_changed_at = result.scalar_one_or_none()
        if not last_changed_at:
            return datetime.strptime("2000-01-01", "%Y-%m-%d").replace(tzinfo=UTC)
        return last_changed_at

    async def _update_sync_metadata(
        self, status: str, message: str, last_changed_at: datetime, sync_type: str
    ) -> None:
        await self.db.execute(
            insert(SyncMetadata).values(
                status=f"{status}: {message}",
                last_changed_at=last_changed_at,
                type=sync_type,
            )
        )
        await self.db.commit()

    async def _fetch_events(
        self, changed_at: datetime, next_url: str | None = None
    ) -> dict[str, Any]:
        headers = {"x-api-key": self.api_token}
        changed_at_date = changed_at.strftime("%Y-%m-%d")

        # If next_url wasnt provided, use changed_at_date as query parameter,
        # otherwise disregard changed_at and use 'next' URL string (which includes
        # changed_at and cursor query parameters) provided by API
        if not next_url:
            params = {"changed_at": changed_at_date}
        else:
            self.api_url = next_url
            params = None

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    self.api_url, params=params, headers=headers, timeout=10
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as e:
                log.error(f"API request failed: {e}")
                raise

    async def _save_events(self, events: list[dict[str, Any]]) -> None:
        for event in events:
            stmt = (
                pg_insert(Event)
                .values(
                    id=event["id"],
                    name=event["name"],
                    place=event["place"],
                    event_time=datetime.fromisoformat(event["event_time"]),
                    registration_deadline=datetime.fromisoformat(
                        event["registration_deadline"]
                    ),
                    status=event["status"],
                    number_of_visitors=event["number_of_visitors"],
                    changed_at=datetime.fromisoformat(event["changed_at"]),
                    created_at=datetime.fromisoformat(event["created_at"]),
                    status_changed_at=datetime.fromisoformat(
                        event["status_changed_at"]
                    ),
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={"changed_at": datetime.fromisoformat(event["changed_at"])},
                )
            )
            await self.db.execute(stmt)
        await self.db.commit()
        log.info(f"Parsed {len(events)} events")

    async def sync(self, sync_type: str) -> None:
        last_changed_at = await self._get_last_changed_at()
        log.info(f"Currently saved last_changed_at: {last_changed_at}")

        current_max = last_changed_at
        total_saved = 0
        next_url = None

        while True:
            try:
                data = await self._fetch_events(
                    changed_at=last_changed_at, next_url=next_url
                )
            except Exception as e:
                log.exception("Exception:")
                await self._update_sync_metadata("error", str(e))
                return

            events = data.get("results", [])
            if not events:
                break

            await self._save_events(events)
            total_saved += len(events)

            # Get max 'changed_at' of events on current page
            batch_max = max(datetime.fromisoformat(e["changed_at"]) for e in events)
            current_max = max(current_max, batch_max)

            # Check if there are more pages to parse
            next_url = data.get("next", "")
            if next_url:
                next_url = next_url.replace("http", "https")
            else:
                break

        if current_max > last_changed_at:
            last_changed_at = current_max
            log.info(f"last_changed_at updated to {current_max}")
        else:
            log.info("No new events since last sync")

        await self._update_sync_metadata(
            "success", f"Synced {total_saved} events", last_changed_at, sync_type
        )
        log.info(f"Sync complete, parsed {total_saved} events")
