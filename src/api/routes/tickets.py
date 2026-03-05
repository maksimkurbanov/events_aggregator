from fastapi import APIRouter

ticket_router = APIRouter(prefix="api", tags=["Tickets"])

# @ticket_router.post("/tickets", response_model=)
# async def buy_ticket()
