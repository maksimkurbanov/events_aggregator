from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_ticket_service,
)
from src.schemas.ticket import BuyTicketRequest
from src.services.ticket_service import TicketService
from src.utils.log import get_logger

log = get_logger(__name__)

ticket_router = APIRouter(prefix="/api", tags=["Tickets"])


@ticket_router.post("/tickets", status_code=status.HTTP_201_CREATED)
async def buy_ticket(
    ticket_data: BuyTicketRequest,
    service: Annotated[TicketService, Depends(get_ticket_service)],
):
    log.debug(f"Routes buy_ticket endpoint: {ticket_data=}")
    return await service.buy_ticket(dict(ticket_data))


@ticket_router.delete("/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: UUID, service: Annotated[TicketService, Depends(get_ticket_service)]
):
    return await service.delete_ticket(ticket_id)
