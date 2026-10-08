from datetime import datetime
from pydantic import BaseModel
from app.models.booking_model import BookingStatus


class BookingCreate(BaseModel):
    user_id: int  # JWT aane tak manually pass karo
    service_id: int
    start_time: datetime
    end_time: datetime
    guests: int = 1


class BookingOut(BaseModel):
    id: int
    user_id: int
    provider_id: int
    service_id: int
    start_time: datetime
    end_time: datetime
    guests: int
    total_price: float
    status: BookingStatus

    class Config:
        from_attributes = True
