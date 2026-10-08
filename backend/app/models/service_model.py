from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Service(Base):
    """
    Har provider ke andar bookable units:
    - Hotel    -> room type (e.g. 'Deluxe Room')
    - Restaurant -> table type (e.g. 'Table for 4')
    - Doctor   -> appointment slot type (e.g. 'General Consultation')
    """

    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)

    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    capacity = Column(Integer, default=1)  # guests/seats; doctor ke liye 1
    duration_minutes = Column(Integer, nullable=True)  # doctor appointment duration
    total_units = Column(Integer, default=1)  # kitne rooms/tables/doctor-slots available

    provider = relationship("Provider", back_populates="services")
