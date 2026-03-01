from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database import get_db
from src.utils.sync import run_sync
from fastapi import APIRouter, Depends

sync_router = APIRouter()

@sync_router.post("/api/sync/trigger")
async def manual_sync(db: AsyncSession = Depends(get_db)):
    await run_sync(db)
    return {"status": "sync started"}