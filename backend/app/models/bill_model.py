import enum

from sqlalchemy import Column, Integer, Float, ForeignKey, Enum, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class BillPaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class RestaurantBill(Base):
    __tablename__ = "restaurant_bills"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("restaurant_orders.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    subtotal = Column(Float, nullable=False, default=0.0)
    discount = Column(Float, nullable=False, default=0.0)
    gst = Column(Float, nullable=False, default=0.0)
    service_charge = Column(Float, nullable=False, default=0.0)
    grand_total = Column(Float, nullable=False, default=0.0)

    payment_status = Column(
        Enum(BillPaymentStatus),
        nullable=False,
        default=BillPaymentStatus.pending,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    paid_at = Column(DateTime(timezone=True), nullable=True)
