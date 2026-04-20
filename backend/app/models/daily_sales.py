from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.database import Base


class DailySales(Base):
    __tablename__ = "daily_sales"

    id = Column(Integer, primary_key=True)
    sale_date = Column(Date, nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    flavor_id = Column(Integer, ForeignKey("flavors.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    source = Column(String(20), nullable=False, default="clover")  # 'clover', 'shopify', 'manual'
    synced_to_sheets = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("sale_date", "location_id", "flavor_id", name="uq_daily_sales"),
        Index("idx_daily_sales_date", "sale_date"),
        Index("idx_daily_sales_location_date", "location_id", "sale_date"),
        Index("idx_daily_sales_median_lookup", "location_id", "flavor_id", sale_date.desc()),
    )
