from datetime import datetime
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    user_id: int  # JWT aane tak manually pass karo
    booking_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewOut(BaseModel):
    id: int
    user_id: int
    provider_id: int
    booking_id: int
    rating: int
    comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True
