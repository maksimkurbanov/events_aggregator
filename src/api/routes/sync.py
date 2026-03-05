from fastapi import APIRouter

from src.utils.log import get_logger
from src.utils.sync_service import do_sync

log = get_logger(__name__)
sync_router = APIRouter(tags=["Sync"])


@sync_router.post("/api/sync/trigger")
async def manual_sync():
    return await do_sync(sync_type="manual")
