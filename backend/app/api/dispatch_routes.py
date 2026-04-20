from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dispatch import DispatchPlan
from app.models.flavor import Flavor
from app.models.location import Location
from app.auth.dependencies import get_current_user, require_module
from app.schemas.dispatch import DispatchPlanResponse, DispatchLocationBlock, DispatchRow, DispatchOverride
from app.services.par_calculator import generate_dispatch_plan
from app.services.sheets_sync import sync_dispatch_to_sheets

router = APIRouter()


def _build_dispatch_response(db: Session, plan_date: date) -> DispatchPlanResponse:
    locations = db.query(Location).filter(Location.is_active.is_(True)).order_by(Location.sort_order).all()
    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    flavor_map = {f.id: f for f in flavors}

    loc_blocks = []
    for loc in locations:
        plans = (
            db.query(DispatchPlan)
            .filter(DispatchPlan.plan_date == plan_date, DispatchPlan.location_id == loc.id)
            .all()
        )
        plan_map = {p.flavor_id: p for p in plans}
        rows = []
        total = 0
        for f in flavors:
            p = plan_map.get(f.id)
            effective_send = 0
            if p:
                effective_send = p.override_amount if p.override_amount is not None else p.amount_to_send
            rows.append(DispatchRow(
                flavor_id=f.id,
                flavor_code=f.code,
                flavor_name=f.name,
                sales_trend_median=float(p.sales_trend_median) if p else 0,
                par_value=float(p.par_value) if p else 0,
                adjusted_par=p.adjusted_par if p else 0,
                live_inventory=p.live_inventory if p else 0,
                amount_to_send=p.amount_to_send if p else 0,
                override_amount=p.override_amount if p else None,
                dispatch_status=p.dispatch_status if p else "pending",
            ))
            total += effective_send

        # Overall status for location block
        statuses = [r.dispatch_status for r in rows]
        block_status = "packed" if all(s == "packed" for s in statuses) else \
                       "sent" if all(s == "sent" for s in statuses) else \
                       "received" if all(s == "received" for s in statuses) else "pending"

        loc_blocks.append(DispatchLocationBlock(
            location_id=loc.id,
            location_name=loc.display_name,
            rows=rows,
            total_to_send=total,
            dispatch_status=block_status,
        ))

    return DispatchPlanResponse(plan_date=plan_date, locations=loc_blocks)


@router.get("/{plan_date}", response_model=DispatchPlanResponse)
def get_dispatch_plan(
    plan_date: date,
    db: Session = Depends(get_db),
    _=Depends(require_module("dispatch")),
):
    return _build_dispatch_response(db, plan_date)


@router.post("/{plan_date}/generate", response_model=DispatchPlanResponse)
def generate_dispatch(
    plan_date: date,
    db: Session = Depends(get_db),
    _=Depends(require_module("dispatch")),
):
    generate_dispatch_plan(db, plan_date)
    # NOTE: Do NOT call sync_dispatch_to_sheets — it would overwrite the
    # sheet's LET/IMPORTRANGE formulas with plain numbers. The sheet computes
    # its own values via IMPORTRANGE from Sales History and Mall PARs.
    resp = _build_dispatch_response(db, plan_date)
    return resp


@router.patch("/{plan_date}/{location_id}/confirm")
def confirm_dispatch(
    plan_date: date,
    location_id: int,
    new_status: str = "packed",
    db: Session = Depends(get_db),
    _=Depends(require_module("dispatch")),
):
    """Mark all flavors for a location as packed/sent/received."""
    updated = (
        db.query(DispatchPlan)
        .filter(DispatchPlan.plan_date == plan_date, DispatchPlan.location_id == location_id)
        .update({"dispatch_status": new_status})
    )
    db.commit()
    return {"status": "ok", "updated": updated, "new_status": new_status}


@router.patch("/{plan_date}/{location_id}/{flavor_id}")
def override_dispatch(
    plan_date: date,
    location_id: int,
    flavor_id: int,
    body: DispatchOverride,
    db: Session = Depends(get_db),
    _=Depends(require_module("dispatch")),
):
    plan = (
        db.query(DispatchPlan)
        .filter(
            DispatchPlan.plan_date == plan_date,
            DispatchPlan.location_id == location_id,
            DispatchPlan.flavor_id == flavor_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Dispatch plan not found")
    plan.override_amount = body.override_amount
    plan.synced_to_sheets = False
    db.commit()
    # Do NOT sync to sheets — would overwrite formulas
    return {"status": "ok"}
