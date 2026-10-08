import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, Text
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

    # Doctor-specific (dusre categories ke liye null rahega)
    specialization = Column(String, nullable=True)

    city = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    avg_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)

    services = relationship("Service", back_populates="provider", cascade="all, delete-orphan")
