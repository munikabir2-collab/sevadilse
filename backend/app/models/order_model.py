import enum

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class OrderType(str, enum.Enum):
    dine_in = "dine_in"
    takeaway = "takeaway"
    delivery = "delivery"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    preparing = "preparing"
    ready = "ready"
    served = "served"
    completed = "completed"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    unpaid = "unpaid"
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class RestaurantOrder(Base):
    __tablename__ = "restaurant_orders"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False,
        index=True,
    )
    table_id = Column(
        Integer,
        ForeignKey("restaurant_tables.id"),
        nullable=True,
        index=True,
    )

    order_type = Column(
        Enum(OrderType),
        nullable=False,
        default=OrderType.dine_in,
    )

    status = Column(
        Enum(OrderStatus),
        nullable=False,
        default=OrderStatus.pending,
    )

    payment_status = Column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.unpaid,
    )

    subtotal = Column(Float, nullable=False, default=0.0)
    discount = Column(Float, nullable=False, default=0.0)
    gst = Column(Float, nullable=False, default=0.0)
    service_charge = Column(Float, nullable=False, default=0.0)
    grand_total = Column(Float, nullable=False, default=0.0)

    special_instructions = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    items = relationship(
        "RestaurantOrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class RestaurantOrderItem(Base):
    __tablename__ = "restaurant_order_items"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("restaurant_orders.id"),
        nullable=False,
        index=True,
    )

    menu_item_id = Column(
        Integer,
        ForeignKey("menu_items.id"),
        nullable=False,
    )

    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    order = relationship(
        "RestaurantOrder",
        back_populates="items",
    )
