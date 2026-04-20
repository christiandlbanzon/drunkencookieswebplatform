from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Flavor(Base):
    __tablename__ = "flavors"

    id = Column(Integer, primary_key=True)
    code = Column(String(5), nullable=False, unique=True)  # 'A' through 'N', 'S1', 'S2'
    name = Column(String(100), nullable=False, unique=True)
    sort_order = Column(Integer, nullable=False)
    is_core = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    category = Column(String(20), nullable=False, default="cookie")  # 'cookie' or 'shot'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
