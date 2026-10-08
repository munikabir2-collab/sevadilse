import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
)

from sqlalchemy.sql import func

from app.core.database import Base


class PayoutAccountStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"


class ProviderPayoutProfile(Base):
    __tablename__ = "provider_payout_profiles"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # SERVICEHUB PROVIDER
    # ========================================================

    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ========================================================
    # RAZORPAY ROUTE LINKED ACCOUNT
    # ========================================================

    razorpay_account_id = Column(
        String,
        nullable=True,
        unique=True,
        index=True,
    )

    # ========================================================
    # RAZORPAY STAKEHOLDER / KYC
    # ========================================================

    razorpay_stakeholder_id = Column(
        String,
        nullable=True,
        unique=True,
        index=True,
    )

    # ========================================================
    # RAZORPAY ROUTE PRODUCT
    # ========================================================

    razorpay_product_id = Column(
        String,
        nullable=True,
        unique=True,
        index=True,
    )

    # ========================================================
    # LOCAL PAYOUT STATUS
    # ========================================================

    status = Column(
        Enum(PayoutAccountStatus),
        nullable=False,
        default=PayoutAccountStatus.pending,
    )

    # ========================================================
    # PAYOUT ENABLED
    # ========================================================

    payouts_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # ========================================================
    # TIMESTAMPS
    # ========================================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )