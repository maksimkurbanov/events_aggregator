from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.services.event_service import EventNotFoundError, EventNotPublishedError
from src.services.ticket_service import (
    TicketRegistrationFailedError,
    TicketBadDataError,
    TicketCancellationFailedError,
    TicketNotFoundError,
)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field = error["loc"][-1]
        msg = error["msg"]
        error_messages.append(f"Invalid input for field '{field}': {msg}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": "Invalid request", "details": error_messages},
    )


async def event_not_found_handler(request: Request, exc: EventNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def event_not_published_handler(request: Request, exc: EventNotPublishedError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


async def ticket_registration_bad_data_handler(
    request: Request, exc: TicketBadDataError
):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


async def ticket_registration_failed_handler(
    request: Request, exc: TicketRegistrationFailedError
):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def ticket_cancellation_failed_handler(
    request: Request, exc: TicketCancellationFailedError
):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def ticket_not_found_handler(request: Request, exc: TicketNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
