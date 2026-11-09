from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    DateTime,
    CheckConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class AdminSettings(Base):
    __tablename__ = "admin_settings"

    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="ck_admin_settings_singleton",
        ),
        CheckConstraint(
            "platform_commission_percent >= 0 AND "
            "platform_commission_percent <= 100",
            name="ck_admin_settings_commission",
        ),
    )

    id = Column(Integer, primary_key=True, default=1)

    platform_name = Column(
        String(150),
        nullable=False,
        default="ServiceHub",
    )

    support_email = Column(String(255), nullable=True)
    support_phone = Column(String(30), nullable=True)

    customer_registration_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    provider_registration_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    booking_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    maintenance_mode = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    platform_commission_percent = Column(
        Numeric(5, 2),
        nullable=False,
        default=10.00,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )