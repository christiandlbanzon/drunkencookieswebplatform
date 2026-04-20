from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)  # "San Patricio"
    display_name = Column(String(100), nullable=False)  # "San Patricio"
    clover_merchant_id = Column(String(50))
    clover_api_token = Column(String(200))
    cookie_category_id = Column(String(50))
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
