from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class DeliveryRequest(Base):
    __tablename__ = "delivery_requests"

    id = Column(Integer, primary_key=True)
    request_date = Column(Date, nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    requested_by = Column(String(100), default="")
    status = Column(String(20), default="pending")  # pending, accepted, completed, rejected
    notes = Column(Text, default="")
    items_requested = Column(Text, default="")  # JSON or comma-separated flavor list
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
