from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class Notification(Base):
    """
    In-app notifications.

    kind:
      - delivery_request: store manager requested 2nd delivery
      - low_stock: location hit >80% sell-through
      - missing_closing: closing inventory not entered by cutoff time
      - info: generic

    target_role: who should see it ('dispatch', 'ops_manager', 'admin', etc.)
    target_user_id: if set, only this user sees it
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    kind = Column(String(30), nullable=False)
    severity = Column(String(10), nullable=False, default="info")  # info, warning, critical
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    target_role = Column(String(30), nullable=True)  # broadcast to a role
    target_user_id = Column(Integer, nullable=True)  # OR direct to one user
    link_url = Column(String(500), nullable=True)  # optional deep link in the app
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
