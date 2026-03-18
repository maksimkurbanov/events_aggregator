from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from src.api.dependencies import get_sync_service
from src.utils.log import get_logger
from src.services.sync_service import SyncService

log = get_logger(__name__)
sync_router = APIRouter(tags=["Sync"])


@sync_router.post("/api/sync/trigger")
async def manual_sync(
    service: Annotated[SyncService, Depends(get_sync_service)],
) -> JSONResponse:
    return await service.do_sync_with_lock(sync_type="manual")
