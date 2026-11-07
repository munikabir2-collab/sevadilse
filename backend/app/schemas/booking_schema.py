from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from app.models.booking_model import BookingStatus


class BookingCreate(BaseModel):
    # Backward compatibility: purane clients user_id bhej sakte hain,
    # lekin Backend is value par trust nahi karega.
    user_id: Optional[int] = None

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


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
