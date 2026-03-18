import asyncio
import random
from datetime import datetime, UTC, timedelta

import httpx

from src.config import dev_settings
from src.database.database import async_session_local
from src.crud.outbox import outbox_crud
from src.external.capashino import CapashinoClient
from src.models.outbox import OutboxStatus, Outbox
from src.schemas.outbox import OutboxUpdate
from src.utils.log import get_logger

log = get_logger(__name__)

BASE_DELAY = 1
MAX_RETRIES = dev_settings.OUTBOX_MAX_RETRIES


async def process_outbox() -> None:
    """
    Fetch pending Outbox events from DB, attempt sending them to Capashino
    Notifications API, if successful mark as sent in DB
    Return None
    """
    async with async_session_local() as db:
        pending = await outbox_crud.get_many_with_lock(
            db,
            Outbox.status == OutboxStatus.PENDING,
            Outbox.retry_count < dev_settings.OUTBOX_MAX_RETRIES,
            order_by=Outbox.created_at,
            limit=50,
        )

        for event in pending:
            async with db.begin_nested():
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        async with CapashinoClient() as client:
                            await client.send_notification(event.payload)
                        await outbox_crud.update(
                            db, event, OutboxUpdate(status=OutboxStatus.SENT)
                        )
                        break
                    except (httpx.HTTPStatusError, httpx.RequestError) as e:
                        log.warning(
                            f"Attempt {attempt}/{MAX_RETRIES} failed for outbox {event.id}: {e}"
                        )
                        if isinstance(
                            e, httpx.HTTPStatusError
                        ) and e.response.status_code in (400, 401, 404, 409, 422):
                            log.error("Encountered critical error, aborting retries")
                            await outbox_crud.update(
                                db, event, OutboxUpdate(retry_count=MAX_RETRIES)
                            )
                            break

                        await outbox_crud.update(
                            db,
                            event,
                            OutboxUpdate(retry_count=event.retry_count + 1),
                        )
                        if event.retry_count == MAX_RETRIES:
                            log.error(f"All retries exhausted for outbox {event.id}")
                        else:
                            delay = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(
                                0, 1
                            )
                            await asyncio.sleep(delay)
        await db.commit()


async def reset_failed() -> None:
    """
    Reset retry_count back to 0 for all Outbox events that reached max_retries
    attempts, yet are still in pending status in DB
    Return None
    """
    log.info("Starting failed events reset job")
    async with async_session_local() as db:
        failed_events = await outbox_crud.get_many_with_lock(
            db,
            Outbox.status == OutboxStatus.PENDING,
            Outbox.retry_count == MAX_RETRIES,
            order_by=Outbox.created_at,
            limit=(2**63 - 1),
        )
        log.info(f"Failed events found: {len(failed_events)}")

        for event in failed_events:
            await outbox_crud.update(db, event, OutboxUpdate(retry_count=0))
        await db.commit()


async def delete_old() -> None:
    """
    Delete all Outbox events that were successfully sent
    and are older than OUTBOX_EVENTS_LIFESPAN_HOURS
    Return None
    """
    log.info("Starting old events deletion job")
    async with async_session_local() as db:
        old_events = await outbox_crud.get_many_with_lock(
            db,
            Outbox.status == OutboxStatus.SENT,
            Outbox.updated_at
            < datetime.now(UTC)
            - timedelta(hours=dev_settings.OUTBOX_EVENTS_LIFESPAN_HOURS),
            order_by=Outbox.created_at,
            limit=(2 * 63 - 1),
        )
        log.info(f"Old events found: {len(old_events)}")

        for event in old_events:
            await outbox_crud.delete(db, event)
        await db.commit()
