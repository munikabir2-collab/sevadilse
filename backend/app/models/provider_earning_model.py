import enum

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Enum,
    ForeignKey,
)

from sqlalchemy.sql import func

from app.core.database import Base


class EarningStatus(str, enum.Enum):
    pending = "pending"
    eligible = "eligible"
    settled = "settled"
    reversed = "reversed"


class ProviderEarning(Base):
    __tablename__ = "provider_earnings"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False,
        index=True,
    )

    payment_id = Column(
        Integer,
        ForeignKey("payments.id"),
        nullable=False,
        index=True,
    )

    gross_amount = Column(
        Float,
        nullable=False,
    )

    commission_percent = Column(
        Float,
        nullable=False,
        default=5.0,
    )

    commission_amount = Column(
        Float,
        nullable=False,
    )

    provider_amount = Column(
        Float,
        nullable=False,
    )

    currency = Column(
        String,
        nullable=False,
        default="INR",
    )

    status = Column(
        Enum(EarningStatus),
        nullable=False,
        default=EarningStatus.pending,
    )

    settlement_reference = Column(
        String,
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    settled_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )