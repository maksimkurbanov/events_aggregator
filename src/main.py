import asyncio
from contextlib import asynccontextmanager

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from src.api.routes.health import health_router
from src.api.routes.sync import sync_router
from src.config import dev_settings
from src.database.database import get_ctx_db, get_engine
from src.log import get_logger
from src.models.base_class import Base
from src.utils.sync_service import do_sync

log = get_logger(__name__)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, start scheduler
    engine = get_engine(dev_settings.POSTGRES_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Schedule daily sync at 2 AM
    scheduler.add_job(
        do_sync, CronTrigger(hour=2, minute=0), args=["scheduled", get_ctx_db]
    )
    # scheduler.add_job(do_sync, 'interval', seconds=5, args=["scheduled", get_ctx_db])
    scheduler.start()
    log.info("Scheduler started")
    yield
    scheduler.shutdown()
    await engine.dispose()


app = FastAPI(lifespan=lifespan, title="Events Aggregator API")
app.include_router(sync_router)
app.include_router(health_router)


async def main():
    config = uvicorn.Config(
        app=app, host="0.0.0.0", port=dev_settings.SERVER_PORT, reload=True
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
