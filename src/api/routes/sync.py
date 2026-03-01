from fastapi import APIRouter

from src.utils.sync_service import do_sync

sync_router = APIRouter()


@sync_router.post("/api/sync/trigger")
async def manual_sync():
    await do_sync(sync_type="manual")
    return {"status": "Sync complete"}
