from uuid import UUID

from pydantic import BaseModel, Field


class PlaceResponse(BaseModel):
    id: UUID
    name: str
    city: str
    address: str


class PlaceWithSeatsResponse(PlaceResponse):
    seats_pattern: str = Field(pattern=r"^(,?([A-Z][1-9]-[1-9]\d*))+$")
