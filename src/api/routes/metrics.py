from typing import Annotated

from fastapi import Response, APIRouter, Depends
from prometheus_client import generate_latest, REGISTRY, Gauge

from src.api.dependencies import get_event_service
from src.services.event_service import EventService

metrics_router = APIRouter(tags=["metrics"])

events_total = Gauge("events_total", "Total number of events")


@metrics_router.get("/metrics")
async def metrics(
    service: Annotated[EventService, Depends(get_event_service)],
):
    count = await service.get_events_count()
    events_total.set(count)

    return Response(content=generate_latest(REGISTRY), media_type="text/plain")
