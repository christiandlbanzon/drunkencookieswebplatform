from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.database import Base


class DispatchPlan(Base):
    __tablename__ = "dispatch_plans"

    id = Column(Integer, primary_key=True)
    plan_date = Column(Date, nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    flavor_id = Column(Integer, ForeignKey("flavors.id"), nullable=False)
    sales_trend_median = Column(Numeric(10, 2), default=0)  # 4-week median (Col B)
    par_value = Column(Numeric(10, 2), default=0)  # 2-day PAR minus reduction (Col C)
    adjusted_par = Column(Integer, default=0)  # MAX(par_value, minimum_par) (Col D)
    live_inventory = Column(Integer, default=0)  # closing from previous day (Col E)
    amount_to_send = Column(Integer, default=0)  # MAX(adjusted_par - live_inventory, 0) (Col F)
    override_amount = Column(Integer, nullable=True)  # manual override
    dispatch_status = Column(String(20), default="pending")  # pending, packed, sent, received
    synced_to_sheets = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("plan_date", "location_id", "flavor_id", name="uq_dispatch_plan"),
        Index("idx_dispatch_date", "plan_date"),
    )
