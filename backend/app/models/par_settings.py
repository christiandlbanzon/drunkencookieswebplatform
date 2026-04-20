from sqlalchemy import Column, Integer, Numeric, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class ParSettings(Base):
    __tablename__ = "par_settings"

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    effective_date = Column(Date, nullable=False)
    reduction_pct = Column(Numeric(5, 2), nullable=False, default=0.00)  # e.g. 0.07 = 7%
    minimum_par = Column(Integer, nullable=False, default=10)
    median_weeks = Column(Integer, nullable=False, default=4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("location_id", "effective_date", name="uq_par_settings"),
    )
