from pydantic import BaseModel
from datetime import date


class BakeRow(BaseModel):
    flavor_id: int
    flavor_code: str
    flavor_name: str
    amount_to_bake: int
    cooking_priority: int | None = None
    website_demand: int
    missing_for_malls: int
    closing_inv_yesterday: int
    mall_forecast: float
    sales_trend_median: float
    total_projection: int
    override_amount: int | None = None

    model_config = {"from_attributes": True}


class BakePlanResponse(BaseModel):
    plan_date: date
    rows: list[BakeRow]
    total_to_bake: int
    total_closing_inventory: int
    sync_warning: str | None = None


class BakeOverride(BaseModel):
    override_amount: int | None = None
    cooking_priority: int | None = None
    website_demand: int | None = None
