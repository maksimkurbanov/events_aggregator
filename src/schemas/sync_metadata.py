from datetime import datetime

from pydantic import BaseModel


class SyncMetadataCreate(BaseModel):
    status: str
    last_changed_at: datetime
    type: str
