from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bake_plan import BakePlan
from app.models.flavor import Flavor
from app.auth.dependencies import require_module
from app.schemas.bake import BakePlanResponse, BakeRow, BakeOverride
from app.services.par_calculator import generate_bake_plan
from app.services.sheets_sync import sync_bake_to_sheets

router = APIRouter()


def _build_bake_response(db: Session, plan_date: date) -> BakePlanResponse:
    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    plans = db.query(BakePlan).filter(BakePlan.plan_date == plan_date).all()
    plan_map = {p.flavor_id: p for p in plans}

    rows = []
    total_bake = 0
    total_closing = 0

    for f in flavors:
        p = plan_map.get(f.id)
        effective_bake = 0
        if p:
            effective_bake = p.override_amount if p.override_amount is not None else p.amount_to_bake
        rows.append(BakeRow(
            flavor_id=f.id,
            flavor_code=f.code,
            flavor_name=f.name,
            amount_to_bake=p.amount_to_bake if p else 0,
            cooking_priority=p.cooking_priority if p else None,
            website_demand=p.website_demand if p else 0,
            missing_for_malls=p.missing_for_malls if p else 0,
            closing_inv_yesterday=p.closing_inv_yesterday if p else 0,
            mall_forecast=float(p.mall_forecast) if p else 0,
            sales_trend_median=float(p.sales_trend_median) if p else 0,
            total_projection=p.total_projection if p else 0,
            override_amount=p.override_amount if p else None,
        ))
        total_bake += effective_bake
        total_closing += (p.closing_inv_yesterday if p else 0)

    return BakePlanResponse(
        plan_date=plan_date,
        rows=rows,
        total_to_bake=total_bake,
        total_closing_inventory=total_closing,
    )


@router.get("/{plan_date}", response_model=BakePlanResponse)
def get_bake_plan(
    plan_date: date,
    db: Session = Depends(get_db),
    _=Depends(require_module("bake")),
):
    return _build_bake_response(db, plan_date)


@router.post("/{plan_date}/generate", response_model=BakePlanResponse)
def generate_bake(
    plan_date: date,
    db: Session = Depends(get_db),
    _=Depends(require_module("bake")),
):
    generate_bake_plan(db, plan_date)
    # NOTE: Do NOT call sync_bake_to_sheets — it would overwrite the
    # sheet's =MAX(0,I-F)+E and IMPORTRANGE formulas with plain numbers.
    resp = _build_bake_response(db, plan_date)
    return resp


@router.patch("/{plan_date}/{flavor_id}")
def override_bake(
    plan_date: date,
    flavor_id: int,
    body: BakeOverride,
    db: Session = Depends(get_db),
    _=Depends(require_module("bake")),
):
    plan = (
        db.query(BakePlan)
        .filter(BakePlan.plan_date == plan_date, BakePlan.flavor_id == flavor_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Bake plan not found")
    if body.override_amount is not None:
        plan.override_amount = body.override_amount
    if body.cooking_priority is not None:
        plan.cooking_priority = body.cooking_priority
    if body.website_demand is not None:
        plan.website_demand = body.website_demand
    plan.synced_to_sheets = False
    db.commit()
    # Do NOT sync to sheets — would overwrite formulas
    return {"status": "ok"}
