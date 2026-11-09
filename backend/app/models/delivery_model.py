"""
Home Delivery module - DATABASE MODELS
Naye tables (existing tables ko ye file chhuti nahi):
    delivery_staff, delivery_orders, delivery_status_logs
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class DeliveryStaffRole(str, enum.Enum):
    sub_admin = "sub_admin"
    delivery_boy = "delivery_boy"


class DeliveryOrderStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    assigned = "assigned"
    picked_up = "picked_up"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
    rejected = "rejected"


class DeliveryPaymentMethod(str, enum.Enum):
    cod = "cod"
    online = "online"


class DeliveryPaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


# ============================================================
# STAFF  (sub-admin / delivery boy) - area wise
# ============================================================

class DeliveryStaff(Base):
    __tablename__ = "delivery_staff"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    role = Column(
        Enum(DeliveryStaffRole, name="delivery_staff_role"),
        nullable=False,
        index=True,
    )

    # normalised (lowercase) area, e.g. "kankarbagh"
    area = Column(String, nullable=False, index=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# DELIVERY ORDER
# ============================================================

class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"

    id = Column(Integer, primary_key=True, index=True)

    # customer
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # optional link: restaurant / shop provider
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True, index=True)

    # optional link: existing restaurant order
    restaurant_order_id = Column(
        Integer,
        ForeignKey("restaurant_orders.id"),
        nullable=True,
        index=True,
    )

    # customer details
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    landmark = Column(String, nullable=True)
    area = Column(String, nullable=False, index=True)

    # order details
    items_description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # money
    order_amount = Column(Float, nullable=False, default=0.0)
    delivery_charge = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)

    payment_method = Column(
        Enum(DeliveryPaymentMethod, name="delivery_payment_method"),
        nullable=False,
        default=DeliveryPaymentMethod.cod,
    )

    payment_status = Column(
        Enum(DeliveryPaymentStatus, name="delivery_payment_status"),
        nullable=False,
        default=DeliveryPaymentStatus.pending,
    )

    status = Column(
        Enum(DeliveryOrderStatus, name="delivery_order_status"),
        nullable=False,
        default=DeliveryOrderStatus.pending,
        index=True,
    )

    assigned_to = Column(
        Integer,
        ForeignKey("delivery_staff.id"),
        nullable=True,
        index=True,
    )

    cod_collected = Column(Boolean, nullable=False, default=False)
    cod_collected_at = Column(DateTime(timezone=True), nullable=True)

    cancel_reason = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    delivered_at = Column(DateTime(timezone=True), nullable=True)


# ============================================================
# STATUS / ACTIVITY LOG
# ============================================================

class DeliveryStatusLog(Base):
    __tablename__ = "delivery_status_logs"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("delivery_orders.id"),
        nullable=False,
        index=True,
    )

    status = Column(String, nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    note = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
