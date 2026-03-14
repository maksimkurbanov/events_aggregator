from fastapi import APIRouter, Request

from src.utils.log import get_logger
from src.services.sync_service import do_sync_with_lock

log = get_logger(__name__)
sync_router = APIRouter(tags=["Sync"])


@sync_router.post("/api/sync/trigger")
async def manual_sync(request: Request):
    return await do_sync_with_lock(app=request.app, sync_type="manual")
