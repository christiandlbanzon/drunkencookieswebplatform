from sqlalchemy import Column, Integer, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index, Computed
from sqlalchemy.sql import func
from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    inventory_date = Column(Date, nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    flavor_id = Column(Integer, ForeignKey("flavors.id"), nullable=False)
    beginning_inventory = Column(Integer, default=0)
    sent_cookies = Column(Integer, default=0)  # from dispatch (kitchen staff)
    received_cookies = Column(Integer, default=0)  # confirmed by store
    opening_stock = Column(Integer, Computed("beginning_inventory + received_cookies"))
    live_sales = Column(Integer, default=0)  # auto from Clover
    second_delivery = Column(Integer, default=0)
    closing_inventory = Column(Integer, default=0)  # manual end-of-day
    # Waste tracking (from Mall PARs sheet cols J-N)
    expired = Column(Integer, default=0)
    flawed = Column(Integer, default=0)  # broken, cracked, crushed
    used_as_display = Column(Integer, default=0)
    given_away = Column(Integer, default=0)  # samples
    production_waste = Column(Integer, default=0)  # misshapen, soft, over/underbake
    synced_to_sheets = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("inventory_date", "location_id", "flavor_id", name="uq_inventory"),
        Index("idx_inventory_date_location", "inventory_date", "location_id"),
    )
