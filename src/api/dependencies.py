from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.events import events_crud
from src.database.database import get_db
from src.models.event import Event


async def verified_event(
    event_id: UUID, check_published: bool, db: Annotated[AsyncSession, Depends(get_db)]
) -> Event:
    """
    Retrieve an event by ID and verify it exists,
    also optionally verify if it is published.
    Raises 404 if not found, 403 if not published.
    Return verified Event object
    """
    event = await events_crud.get_one(db, Event.id == event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found",
        )
    if check_published and event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Event with ID {event_id} not published",
        )
    return event


async def event_exists(
    event_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> Event:
    """
    Wrapper for verified_event for correct dependency injection function signature handling:
    Verify that an event exists (published status not required)
    """
    return await verified_event(event_id, check_published=False, db=db)


async def event_exists_and_published(
    event_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> Event:
    """
    Wrapper for verified_event for correct dependency injection function signature handling:
    Verify that an event exists and is published
    """
    return await verified_event(event_id, check_published=True, db=db)
