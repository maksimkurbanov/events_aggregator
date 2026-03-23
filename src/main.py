import asyncio
from contextlib import asynccontextmanager

import sentry_sdk
from prometheus_client import start_http_server
from sentry_sdk.integrations.fastapi import FastApiIntegration
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from src.api.exception_handlers import (
    validation_exception_handler,
    domain_exception_handler,
)
from src.api.routes.events import events_router
from src.api.routes.exceptions import DomainError
from src.api.routes.health import health_router
from src.api.routes.metrics import metrics_router
from src.api.routes.sync import sync_router
from src.api.routes.tickets import ticket_router
from src.config import dev_settings
from src.database.database import get_ctx_db, engine
from src.middleware.metrics_middleware import MetricsMiddleware
from src.services.outbox_service import (
    outbox_process_events,
    outbox_reset_failed_events,
    outbox_delete_old_events,
)

from src.utils.log import get_logger
from src.services.sync_service import do_sync

log = get_logger(__name__)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = engine

    scheduler.add_job(
        do_sync,
        CronTrigger(hour=2, minute=0),
        max_instances=1,
        args=["scheduled", get_ctx_db],
        id="events_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        outbox_process_events,
        "interval",
        seconds=5,
        max_instances=1,
        id="outbox_process_events",
        replace_existing=True,
    )
    scheduler.add_job(
        outbox_reset_failed_events,
        "interval",
        minutes=60,
        max_instances=1,
        id="outbox_reset_failed_events",
        replace_existing=True,
    )
    scheduler.add_job(
        outbox_delete_old_events,
        CronTrigger(hour=6, minute=0),
        max_instances=1,
        id="outbox_delete_old_events",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler started")
    yield
    scheduler.shutdown()
    await engine.dispose()


sentry_sdk.init(
    dsn=dev_settings.SENTRY_DSN,
    traces_sample_rate=1.0,
    integrations=[FastApiIntegration()],
)


app = FastAPI(lifespan=lifespan, title="Events Aggregator API")

app.add_middleware(MetricsMiddleware)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(DomainError, domain_exception_handler)


app.include_router(sync_router)
app.include_router(health_router)
app.include_router(events_router)
app.include_router(ticket_router)
app.include_router(metrics_router)


async def main():
    start_http_server(9090)
    config = uvicorn.Config(
        app=app, host="0.0.0.0", port=dev_settings.SERVER_PORT, reload=True
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
