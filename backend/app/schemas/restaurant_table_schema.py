from pydantic import BaseModel
from app.models.restaurant_table_model import TableStatus


class RestaurantTableCreate(BaseModel):
    table_number: str
    capacity: int = 2
    description: str | None = None


class RestaurantTableUpdate(BaseModel):
    table_number: str | None = None
    capacity: int | None = None
    status: TableStatus | None = None
    description: str | None = None


class RestaurantTableOut(BaseModel):
    id: int
    provider_id: int
    table_number: str
    capacity: int
    status: TableStatus
    description: str | None

    class Config:
        from_attributes = True
