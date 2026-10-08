from datetime import datetime

from pydantic import BaseModel, Field


# =========================================================
# DOCTOR PROFILE
# =========================================================

class DoctorProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    specialization: str | None = None
    description: str | None = None
    city: str | None = Field(default=None, min_length=1)
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class DoctorOut(BaseModel):
    id: int
    owner_id: int
    name: str
    category: str
    description: str | None
    specialization: str | None
    city: str
    address: str | None
    latitude: float | None
    longitude: float | None
    avg_rating: float
    total_reviews: int

    class Config:
        from_attributes = True


# =========================================================
# DOCTOR SLOT
# =========================================================

class DoctorSlotCreate(BaseModel):
    service_id: int
    start_time: datetime
    end_time: datetime


class DoctorSlotUpdate(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_available: bool | None = None


class DoctorSlotOut(BaseModel):
    id: int
    provider_id: int
    service_id: int
    start_time: datetime
    end_time: datetime
    is_available: bool

    class Config:
        from_attributes = True


# =========================================================
# APPOINTMENT
# =========================================================

class AppointmentCreate(BaseModel):
    user_id: int
    provider_id: int
    service_id: int
    slot_id: int


class AppointmentOut(BaseModel):
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