from pydantic import BaseModel
from app.models.provider_model import ProviderCategory


class ServiceCreate(BaseModel):
    name: str
    price: float
    capacity: int = 1
    duration_minutes: int | None = None
    total_units: int = 1


class ServiceOut(BaseModel):
    id: int
    name: str
    price: float
    capacity: int
    duration_minutes: int | None
    total_units: int

    class Config:
        from_attributes = True


class ProviderCreate(BaseModel):
    name: str
    category: ProviderCategory
    description: str | None = None
    specialization: str | None = None  # sirf doctor ke liye
    city: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ProviderOut(BaseModel):
    id: int
    name: str
    category: ProviderCategory
    description: str | None
    specialization: str | None
    city: str
    phone: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    avg_rating: float
    total_reviews: int

    class Config:
        from_attributes = True


class ProviderDetailOut(ProviderOut):
    services: list[ServiceOut] = []



class ProviderUpdate(BaseModel):
    name: str | None = None
    category: ProviderCategory | None = None
    description: str | None = None
    specialization: str | None = None
    city: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ServiceUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    capacity: int | None = None
    duration_minutes: int | None = None
    total_units: int | None = None
