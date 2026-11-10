
"""
Home Delivery v2 - DATABASE MODELS

Legacy tables and columns are preserved.
Hierarchy:
Platform Super Admin -> City Main Admin -> Area Admin
-> Delivery Boys (multiple area assignments)
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
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class DeliveryStaffRole(str, enum.Enum):
    # Keep legacy role for compatibility
    sub_admin = "sub_admin"
    area_admin = "area_admin"
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


# CITY
class DeliveryCity(Base):
    __tablename__ = "delivery_cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# AREA
class DeliveryArea(Base):
    __tablename__ = "delivery_areas"

    __table_args__ = (
        UniqueConstraint("city_id", "name", name="uq_delivery_area_city_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(
        Integer,
        ForeignKey("delivery_cities.id"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# PIN CODE
class DeliveryPincode(Base):
    __tablename__ = "delivery_pincodes"

    id = Column(Integer, primary_key=True, index=True)
    pincode = Column(String(6), nullable=False, unique=True, index=True)
    area_id = Column(
        Integer,
        ForeignKey("delivery_areas.id"),
        nullable=False,
        index=True,
    )
    # Inactive until service coverage is verified
    is_active = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# CITY MAIN ADMIN
class DeliveryCityAdmin(Base):
    __tablename__ = "delivery_city_admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    city_id = Column(
        Integer,
        ForeignKey("delivery_cities.id"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# DELIVERY STAFF (legacy area field retained)
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
    area = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# MULTIPLE AREA ASSIGNMENTS FOR STAFF
class DeliveryStaffArea(Base):
    __tablename__ = "delivery_staff_areas"

    __table_args__ = (
        UniqueConstraint("staff_id", "area_id", name="uq_delivery_staff_area"),
    )

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(
        Integer,
        ForeignKey("delivery_staff.id"),
        nullable=False,
        index=True,
    )
    area_id = Column(
        Integer,
        ForeignKey("delivery_areas.id"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# DELIVERY ORDER
class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True, index=True)
    restaurant_order_id = Column(
        Integer,
        ForeignKey("restaurant_orders.id"),
        nullable=True,
        index=True,
    )

    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    landmark = Column(String, nullable=True)

    # New hierarchy fields; nullable for old orders
    pincode = Column(String(6), nullable=True, index=True)
    area_id = Column(
        Integer,
        ForeignKey("delivery_areas.id"),
        nullable=True,
        index=True,
    )
    city_id = Column(
        Integer,
        ForeignKey("delivery_cities.id"),
        nullable=True,
        index=True,
    )

    # Legacy area retained
    area = Column(String, nullable=False, index=True)

    items_description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

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


# DELIVERY STATUS LOG
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
