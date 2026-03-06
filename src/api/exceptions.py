from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError

from src.main import app


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    custom_messages = []
    for error in errors:
        field = error["loc"][-1]
        msg = error["msg"]
        custom_messages.append(f"Invalid input for field '{field}': {msg}")

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"message": "Invalid request", "details": custom_messages},
    )
