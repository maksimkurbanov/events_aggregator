from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Place(BaseModel):
    id: UUID
    name: str
    city: str
    address: str
    seats_pattern: str = Field(pattern=r"^(,?([A-Z][1-9]-[1-9]\d*))+$")
    changed_at: datetime
    created_at: datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PlaceResponse(BaseModel):
    id: UUID
    name: str
    city: str
    address: str

    model_config = ConfigDict(from_attributes=True)
