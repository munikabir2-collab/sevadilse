from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class DoctorSlot(Base):
    __tablename__ = "doctor_slots"

    id = Column(Integer, primary_key=True, index=True)

    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False,
        index=True,
    )

    service_id = Column(
        Integer,
        ForeignKey("services.id"),
        nullable=False,
        index=True,
    )

    start_time = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    end_time = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    is_available = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    provider = relationship("Provider")
    service = relationship("Service")