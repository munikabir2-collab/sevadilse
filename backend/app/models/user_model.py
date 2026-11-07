
from sqlalchemy import Column, Integer, String, Boolean, text
from app.core.database import Base
from sqlalchemy.orm import synonym


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = synonym("hashed_password")
    hashed_password = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    is_provider = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
