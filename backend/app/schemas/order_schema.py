from datetime import datetime
from pydantic import BaseModel, Field

from app.models.order_model import (
    OrderType,
    OrderStatus,
    PaymentStatus,
)


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(default=1, ge=1)


class OrderCreate(BaseModel):
    user_id: int
    provider_id: int
    table_id: int | None = None
    order_type: OrderType = OrderType.dine_in
    items: list[OrderItemCreate] = Field(min_length=1)
    discount: float = Field(default=0.0, ge=0)
    gst_percent: float = Field(default=5.0, ge=0)
    service_charge_percent: float = Field(default=0.0, ge=0)
    special_instructions: str | None = None


class OrderItemOut(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    user_id: int
    provider_id: int
    table_id: int | None
    order_type: OrderType
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal: float
    discount: float
    gst: float
    service_charge: float
    grand_total: float
    special_instructions: str | None
    created_at: datetime
    items: list[OrderItemOut]

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: OrderStatus