import json
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.log import get_logger
import traceback
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import insert, select, update
from src.database.database import get_db
from src.config import dev_settings

from src.models.sync_metadata import SyncMetadata
from src.models.event import Event

log = get_logger(__name__)


class SyncService:
    def __init__(self, db):
        self.db = db
        self.api_url = dev_settings.EVENT_PROVIDER_URL
        self.api_token = dev_settings.LMS_API_KEY

    async def _get_last_changed_at(self) -> int:
        result = await self.db.execute(
            select(SyncMetadata.value).where(
                SyncMetadata.key == "last_changed_at"
            )
        )
        row = result.scalar_one_or_none()
        return int(row) if row else "2000-01-01"

    async def _update_last_changed_at(self, new_value: int) -> None:
        await self.db.execute(
            update(SyncMetadata)
            .where(SyncMetadata.key == "last_changed_at")
            .values(value=str(new_value))
        )
        await self.db.commit()

    async def _update_sync_metadata(self, status: str, message: str = "") -> None:
        now = datetime.now(tz=UTC)

        await self.db.execute(
            update(SyncMetadata)
            .where(SyncMetadata.key == "last_sync_status")
            .values(value=f"{status}: {message}", updated_at=now)
        )

        await self.db.execute(
            update(SyncMetadata)
            .where(SyncMetadata.key == "last_sync_time")
            .values(value=str(now), updated_at=now)
        )
        await self.db.commit()

    async def _fetch_events(self, changed_at: int, next_url: str = None) -> Dict[str, Any]:
        headers = {"x-api-key": self.api_token}

        if not next_url:
            params = {"changed_at": changed_at}
        else:
            self.api_url = next_url
            params = None


        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    self.api_url, params=params, headers=headers, timeout=10
                )
                log.info("Response from Events Provider", resp)
                resp.raise_for_status()


                return resp.json()
            except httpx.HTTPError as e:
                log.error(f"API request failed: {e}")
                raise

    async def _save_events(self, events: List[Dict[str, Any]]) -> None:
        for event in events:
            stmt = (
                pg_insert(Event)
                .values(
                    id=event["id"],
                    name=event["name"],
                    place_id=event["place"]["id"],
                    event_time=event["event_time"],
                    registration_deadline=event["registration_deadline"],
                    status=event["status"],
                    number_of_visitors=event["number_of_visitors"],
                    changed_at=event["changed_at"],
                    created_at=event["created_at"],
                    status_changed_at=event["status_changed_at"],
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "changed_at": event["changed_at"]
                    },
                )
            )
            await self.db.execute(stmt)
        await self.db.commit()
        log.info(f"Saved/updated {len(events)} events")

    async def sync(self) -> None:
        log.info("Starting sync operation")
        last_changed_at = await self._get_last_changed_at()
        log.info(f"Last saved changed_at: {last_changed_at}")

        current_max = last_changed_at
        total_saved = 0

        while True:
            try:
                data = await self._fetch_events(last_changed_at)
            except Exception as e:
                log.exception("Exception:")
                await self._update_sync_metadata("error", str(e))
                return

            events = data.get("results", [])
            if not events:
                break

            await self._save_events(events)
            total_saved += len(events)

            # Находим максимальный changed_at в этой партии
            batch_max = max(e["changed_at"] for e in events)
            if batch_max > current_max:
                current_max = batch_max

            # Проверяем наличие следующей страницы
            next_url = data.get("next")
            if not next_url:
                break



        if current_max > last_changed_at:
            await self._update_last_changed_at(current_max)
            log.info(f"last_changed_at updated to {current_max}")
        else:
            log.info("No new events since last sync")

        await self._update_sync_metadata("success", f"Synced {total_saved} events")
        log.info(f"Sync complete, synced {total_saved} events")