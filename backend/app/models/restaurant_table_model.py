import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from app.core.database import Base


class TableStatus(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    inactive = "inactive"


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, index=True)

    table_number = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False, default=2)
    status = Column(
        Enum(TableStatus),
        nullable=False,
        default=TableStatus.available,
    )

    description = Column(String, nullable=True)
