from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.schemas.place import PlaceResponse


class Event(BaseModel):
    pass


class EventsRequest(BaseModel):
    date_from: str = Field("2000-01-01", pattern=r"^\d{4}-\d{2}-\d{2}$")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)


class EventsResponse(BaseModel):
    count: int = Field(ge=0)
    next: HttpUrl | None
    previous: HttpUrl | None
    results: list[SingleEventResponse] | None

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
