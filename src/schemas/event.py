from typing import List
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, ConfigDict

from src.schemas.place import PlaceResponse


class Event(BaseModel):
    pass


class EventsResponse(BaseModel):
    count: int = Field(gt=0)
    next: HttpUrl
    previous: HttpUrl
    results: List[SingleEventResponse] | None

    model_config = ConfigDict(from_attributes=True)


class SingleEventResponse(BaseModel):
    id: UUID
    name: str
    place: PlaceResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)
