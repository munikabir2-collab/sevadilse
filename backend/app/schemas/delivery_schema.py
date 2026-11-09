"""
Home Delivery module - REQUEST / RESPONSE SCHEMAS (pydantic v2)
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.delivery_model import (
    DeliveryOrderStatus,
    DeliveryPaymentMethod,
    DeliveryPaymentStatus,
    DeliveryStaffRole,
)


# ============================================================
# ORDER
# ============================================================

class DeliveryOrderCreate(BaseModel):
    provider_id: int | None = None
    restaurant_order_id: int | None = None

    customer_name: str = Field(min_length=1)
    customer_phone: str = Field(min_length=7)
    address: str = Field(min_length=3)
    area: str = Field(min_length=1)
    landmark: str | None = None

    items_description: str | None = None
    # restaurant_order_id dene par amount server khud leta hai
    order_amount: float | None = Field(default=None, ge=0)

    payment_method: DeliveryPaymentMethod = DeliveryPaymentMethod.cod
    notes: str | None = None


class DeliveryOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    provider_id: int | None = None
    restaurant_order_id: int | None = None

    customer_name: str
    customer_phone: str
    address: str
    landmark: str | None = None
    area: str

    items_description: str | None = None
    notes: str | None = None

    order_amount: float
    delivery_charge: float
    total_amount: float

    payment_method: DeliveryPaymentMethod
    payment_status: DeliveryPaymentStatus
    status: DeliveryOrderStatus

    assigned_to: int | None = None

    cod_collected: bool
    cod_collected_at: datetime | None = None
    cancel_reason: str | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None
    delivered_at: datetime | None = None


class AssignRequest(BaseModel):
    staff_id: int


class StatusUpdateRequest(BaseModel):
    status: DeliveryOrderStatus
    note: str | None = None


class ReasonRequest(BaseModel):
    reason: str | None = None


class CODCollectRequest(BaseModel):
    notes: str | None = None


class StatusLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    status: str
    changed_by: int | None = None
    note: str | None = None
    created_at: datetime | None = None


# ============================================================
# STAFF
# ============================================================

class StaffCreate(BaseModel):
    # user pehle app mein signup kar chuka hona chahiye
    email: str = Field(min_length=3)
    role: DeliveryStaffRole
    area: str | None = None


class StaffActiveUpdate(BaseModel):
    is_active: bool


class StaffOut(BaseModel):
    id: int
    user_id: int
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: DeliveryStaffRole
    area: str
    is_active: bool
