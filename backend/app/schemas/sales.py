from pydantic import BaseModel
from datetime import date


class DailySalesRow(BaseModel):
    flavor_id: int
    flavor_code: str
    flavor_name: str
    quantity: int
    source: str

    model_config = {"from_attributes": True}


class DailySalesResponse(BaseModel):
    sale_date: date
    location_id: int
    location_name: str
    rows: list[DailySalesRow]


class MedianResponse(BaseModel):
    location_id: int
    flavor_id: int
    median_value: float
    weeks: int
    data_points: int
