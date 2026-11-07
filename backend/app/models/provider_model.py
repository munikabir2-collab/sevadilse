import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Enum,
    Text,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProviderCategory(str, enum.Enum):
    hotel = "hotel"
    restaurant = "restaurant"
    doctor = "doctor"


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)
    category = Column(Enum(ProviderCategory), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Doctor-specific
    specialization = Column(String, nullable=True)

    city = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    avg_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)

    # Admin Provider Management
    verification_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    rejection_reason = Column(Text, nullable=True)

    verified_at = Column(DateTime(timezone=True), nullable=True)

    verified_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    services = relationship(
        "Service",
        back_populates="provider",
        cascade="all, delete-orphan",
    )