
"""
Home Delivery v2 - REQUEST / RESPONSE SCHEMAS
Pydantic v2
"""

from datetime import datetime
from typing import Literal

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

    # Six digit PIN code
    pincode: str = Field(pattern=r"^\d{6}$")

    # Legacy compatibility only.
    # Actual area must be resolved by backend using PIN code.
    area: str | None = None

    landmark: str | None = None
    items_description: str | None = None
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

    pincode: str | None = None
    area_id: int | None = None
    city_id: int | None = None
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
# CITY
# ============================================================

class CityCreate(BaseModel):
    name: str = Field(min_length=2)


class CityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool


class CityAdminCreate(BaseModel):
    email: str = Field(min_length=3)
    city_id: int


class CityAdminOut(BaseModel):
    id: int
    user_id: int
    name: str | None = None
    email: str | None = None
    city_id: int
    city_name: str | None = None
    is_active: bool


# ============================================================
# AREA
# ============================================================

class AreaCreate(BaseModel):
    city_id: int
    name: str = Field(min_length=2)


class AreaOut(BaseModel):
    id: int
    city_id: int
    city_name: str | None = None
    name: str
    is_active: bool


# ============================================================
# PINCODE
# ============================================================

class PincodeCreate(BaseModel):
    pincode: str = Field(pattern=r"^\d{6}$")
    area_id: int
    is_active: bool = False


class PincodeUpdate(BaseModel):
    area_id: int | None = None
    is_active: bool | None = None


class PincodeOut(BaseModel):
    id: int
    pincode: str
    area_id: int
    area_name: str | None = None
    city_id: int | None = None
    city_name: str | None = None
    is_active: bool


class PincodeCheckOut(BaseModel):
    pincode: str
    serviceable: bool
    area: str | None = None
    city: str | None = None


# ============================================================
# STAFF
# ============================================================

class StaffCreate(BaseModel):
    # User must register before staff creation.
    email: str = Field(min_length=3)

    role: Literal["area_admin", "delivery_boy"]

    # Staff can be assigned to multiple areas.
    area_ids: list[int] = Field(min_length=1)


class StaffAreasUpdate(BaseModel):
    area_ids: list[int] = Field(min_length=1)


class StaffActiveUpdate(BaseModel):
    is_active: bool


class StaffOut(BaseModel):
    id: int
    user_id: int
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: DeliveryStaffRole

    area_ids: list[int] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)

    is_active: bool
