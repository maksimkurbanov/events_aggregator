from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.log import get_logger
from src.database.database import get_engine, get_db
from src.config import dev_settings
from src.api.sync_service import SyncService
from src.models.sync_metadata import SyncMetadata
from src.models.base_class import Base

log = get_logger(__name__)

scheduler = AsyncIOScheduler()

async def run_sync(db: AsyncSession = Depends(get_db)):
    log.info("Running scheduled sync")
    service = SyncService(db)
    await service.sync()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, start scheduler
    engine = get_engine(dev_settings.POSTGRES_DB_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    get_async_session_context = asynccontextmanager(get_db)
    async with get_async_session_context() as db:
        # Initialize metadata if not exists
        result = await db.execute(select(SyncMetadata).where(SyncMetadata.key == 'last_changed_at'))
        if not result.scalar_one_or_none():
            db.add(SyncMetadata(key='last_changed_at', value='0'))
            db.add(SyncMetadata(key='last_sync_status', value='never'))
            db.add(SyncMetadata(key='last_sync_time', value='0'))
            await db.commit()
    # Schedule daily sync at 2 AM
    scheduler.add_job(run_sync, CronTrigger(hour=2, minute=0))
    scheduler.start()
    log.info("Scheduler started")
    yield
    # Shutdown: stop scheduler
    scheduler.shutdown()
