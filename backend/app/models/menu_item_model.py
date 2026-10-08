from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from app.core.database import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, index=True)

    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    price = Column(Float, nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)

    image_url = Column(String, nullable=True)
