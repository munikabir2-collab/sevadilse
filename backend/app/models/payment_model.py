import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum,
    ForeignKey,
)

from sqlalchemy.sql import func

from app.core.database import Base


# ============================================================
# PAYMENT METHOD
# ============================================================

class PaymentMethod(str, enum.Enum):
    online = "online"
    cod = "cod"


# ============================================================
# PAYMENT STATUS
# ============================================================

class PaymentStatus(str, enum.Enum):
    created = "created"
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


# ============================================================
# PAYMENT ENTITY
# ============================================================

class PaymentEntityType(str, enum.Enum):
    restaurant_order = "restaurant_order"
    hotel_booking = "hotel_booking"
    doctor_appointment = "doctor_appointment"
    booking = "booking"


# ============================================================
# PAYMENT MODEL
# ============================================================

class Payment(Base):
    __tablename__ = "payments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # --------------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------------

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # --------------------------------------------------------
    # PROVIDER
    # --------------------------------------------------------

    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=True,
        index=True,
    )

    # --------------------------------------------------------
    # PAYMENT TARGET
    # --------------------------------------------------------

    entity_type = Column(
        Enum(PaymentEntityType),
        nullable=False,
        index=True,
    )

    entity_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    # --------------------------------------------------------
    # PAYMENT METHOD
    # --------------------------------------------------------

    payment_method = Column(
        Enum(PaymentMethod),
        nullable=False,
        default=PaymentMethod.online,
        index=True,
    )

    # --------------------------------------------------------
    # MONEY
    # --------------------------------------------------------

    amount = Column(
        Float,
        nullable=False,
    )

    currency = Column(
        String,
        nullable=False,
        default="INR",
    )

    # --------------------------------------------------------
    # SERVICEHUB COMMISSION
    # --------------------------------------------------------

    commission_percent = Column(
        Float,
        nullable=False,
        default=5.0,
    )

    commission_amount = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    # --------------------------------------------------------
    # PROVIDER EARNING
    # --------------------------------------------------------

    provider_amount = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    # --------------------------------------------------------
    # PAYMENT STATUS
    # --------------------------------------------------------

    status = Column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.created,
        index=True,
    )

    # --------------------------------------------------------
    # RAZORPAY
    # --------------------------------------------------------

    razorpay_order_id = Column(
        String,
        nullable=True,
        unique=True,
        index=True,
    )

    razorpay_payment_id = Column(
        String,
        nullable=True,
        unique=True,
        index=True,
    )

    razorpay_signature = Column(
        String,
        nullable=True,
    )

    # --------------------------------------------------------
    # COD
    # --------------------------------------------------------

    cod_collected_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    cod_collected_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    cod_notes = Column(
        String,
        nullable=True,
    )

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    paid_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )