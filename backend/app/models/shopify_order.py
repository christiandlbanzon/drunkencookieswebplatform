from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Numeric, Text
from sqlalchemy.sql import func
from app.database import Base


class ShopifyOrder(Base):
    __tablename__ = "shopify_orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(20), nullable=False, unique=True, index=True)  # "#5988"
    order_date = Column(Date, nullable=False, index=True)
    customer_name = Column(String(200), default="")
    contact_phone = Column(String(50), default="")
    email = Column(String(200), default="")
    shipping_address = Column(Text, default="")
    gift_message = Column(Text, default="")
    items_summary = Column(Text, default="")  # "2x Chocolate Chip, 1x Brookie"
    tracking_number = Column(String(200), default="")
    delivery_status = Column(String(30), default="Pending")  # Pending, In Transit, Out for Delivery, Delivered, Failed, Cancelled
    is_special_request = Column(Boolean, default=False)
    special_request_type = Column(String(50), default="")  # Wedding, Corporate, Party, Catering
    refund_status = Column(String(10), default="No")  # Yes / No
    refund_amount = Column(Numeric(10, 2), default=0)
    refund_date = Column(Date, nullable=True)
    refund_reason = Column(Text, default="")
    # Manual fields — preserved on sync
    package_notes = Column(Text, default="")
    feedback = Column(Text, default="")
    endorsement = Column(Text, default="")
    total_price = Column(Numeric(10, 2), default=0)
    financial_status = Column(String(30), default="paid")
    synced_to_sheets = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
