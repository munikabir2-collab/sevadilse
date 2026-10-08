from datetime import datetime

from pydantic import BaseModel, Field


class HotelRoomCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    capacity: int = Field(default=1, gt=0)
    total_units: int = Field(default=1, gt=0)


class HotelRoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, gt=0)
    capacity: int | None = Field(default=None, gt=0)
    total_units: int | None = Field(default=None, gt=0)


class HotelRoomOut(BaseModel):
    id: int
    provider_id: int
    name: str
    price: float
    capacity: int
    duration_minutes: int | None
    total_units: int

    class Config:
        from_attributes = True


class HotelBookingCreate(BaseModel):
    user_id: int
    provider_id: int
    service_id: int

    check_in: datetime
    check_out: datetime

    guests: int = Field(default=1, gt=0)


class HotelBookingOut(BaseModel):
    id: int
    user_id: int
    provider_id: int
    service_id: int
    start_time: datetime
    end_time: datetime
    guests: int
    total_price: float
    status: str

    class Config:
        from_attributes = True