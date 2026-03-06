from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlaceResponse(BaseModel):
    id: UUID
    name: str
    city: str
    address: str

    model_config = ConfigDict(from_attributes=True)


class PlaceWithSeatsResponse(PlaceResponse):
    seats_pattern: str = Field(pattern=r"^(,?([A-Z]1-[1-9]\d*))+$")


class PlaceUpdate(PlaceWithSeatsResponse):
    changed_at: datetime
    created_at: datetime
