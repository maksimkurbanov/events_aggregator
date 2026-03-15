from src.database.database import async_session_local
from src.crud.outbox import outbox_crud
from src.external.capashino import CapashinoClient
from src.utils.log import get_logger

log = get_logger(__name__)


async def process_outbox():
    async with async_session_local() as db:
        pending = await outbox_crud.get_pending(db, limit=50)
        if not pending:
            return

        for event in pending:
            async with db.begin_nested():
                try:
                    async with CapashinoClient() as client:
                        await client.send_notification(event.payload)
                    await outbox_crud.mark_sent(db, event.id)
                except Exception as e:
                    log.error(f"Failed to send outbox {event.id}: {e}")
        await db.commit()
