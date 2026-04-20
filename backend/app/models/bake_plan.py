from sqlalchemy import Column, Integer, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.database import Base


class BakePlan(Base):
    __tablename__ = "bake_plans"

    id = Column(Integer, primary_key=True)
    plan_date = Column(Date, nullable=False)
    flavor_id = Column(Integer, ForeignKey("flavors.id"), nullable=False)
    amount_to_bake = Column(Integer, default=0)  # Col B: main output
    cooking_priority = Column(Integer, nullable=True)  # Col C: manual
    website_demand = Column(Integer, default=0)  # Col D: manual
    missing_for_malls = Column(Integer, default=0)  # Col E: calculated
    closing_inv_yesterday = Column(Integer, default=0)  # Col F: from inventory
    mall_forecast = Column(Numeric(10, 2), default=0)  # Col G: sum of dispatch medians
    sales_trend_median = Column(Numeric(10, 2), default=0)  # Col H: 4-week median baseline
    total_projection = Column(Integer, default=0)  # Col I: calculated
    override_amount = Column(Integer, nullable=True)
    synced_to_sheets = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("plan_date", "flavor_id", name="uq_bake_plan"),
        Index("idx_bake_date", "plan_date"),
    )
