import asyncio
from contextlib import asynccontextmanager

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.sql.expression import text

from src.api.exception_handlers import validation_exception_handler
from src.api.routes.events import events_router
from src.api.routes.health import health_router
from src.api.routes.sync import sync_router
from src.api.routes.tickets import ticket_router
from src.config import dev_settings
from src.database.database import get_ctx_db, get_engine
from src.models.base_class import Base
from src.utils.create_lock_key import create_lock_key
from src.utils.log import get_logger
from src.utils.sync_service import do_sync_with_lock

log = get_logger(__name__)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, start scheduler
    engine = get_engine(dev_settings.POSTGRES_DB_URL, echo=False)
    app.state.engine = engine
    async with engine.begin() as conn:
        lock_key = create_lock_key("create_table_schemas")
        result = await conn.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_key}
        )
        lock_acquired = result.scalar()
        if lock_acquired:
            await conn.run_sync(Base.metadata.create_all)
        else:
            log.info("Table creation lock held by another process – skipping")

    # Schedule daily sync at 2 AM
    scheduler.add_job(
        do_sync_with_lock,
        CronTrigger(hour=2, minute=0),
        max_instances=1,
        args=[app, "scheduled", get_ctx_db],
    )
    scheduler.start()
    log.info("Scheduler started")
    yield
    scheduler.shutdown()
    await engine.dispose()


app = FastAPI(lifespan=lifespan, title="Events Aggregator API")
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(sync_router)
app.include_router(health_router)
app.include_router(events_router)
app.include_router(ticket_router)


async def main():
    config = uvicorn.Config(
        app=app, host="0.0.0.0", port=dev_settings.SERVER_PORT, reload=True
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
