"""
Sales analytics endpoints — trend data for charts.
"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.daily_sales import DailySales
from app.models.inventory import Inventory
from app.models.dispatch import DispatchPlan
from app.models.flavor import Flavor
from app.models.location import Location
from app.models.delivery_request import DeliveryRequest
from app.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/trends")
def get_sales_trends(
    days: int = Query(default=30, ge=7, le=90),
    location_id: int | None = None,
    flavor_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Get daily sales trends for charting.
    Returns [{date, location, flavor, quantity}, ...] for the last N days.
    """
    start_date = date.today() - timedelta(days=days)

    query = (
        db.query(
            DailySales.sale_date,
            Location.display_name.label("location"),
            Flavor.name.label("flavor"),
            Flavor.code.label("flavor_code"),
            DailySales.quantity,
        )
        .join(Location, DailySales.location_id == Location.id)
        .join(Flavor, DailySales.flavor_id == Flavor.id)
        .filter(DailySales.sale_date >= start_date)
    )

    if location_id:
        query = query.filter(DailySales.location_id == location_id)
    if flavor_id:
        query = query.filter(DailySales.flavor_id == flavor_id)

    rows = query.order_by(DailySales.sale_date).all()

    return [
        {
            "date": str(r.sale_date),
            "location": r.location,
            "flavor": r.flavor,
            "flavor_code": r.flavor_code,
            "quantity": r.quantity,
        }
        for r in rows
    ]


@router.get("/summary")
def get_sales_summary(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Aggregated sales summary: total per location and per flavor over last N days.
    """
    start_date = date.today() - timedelta(days=days)

    # Per location totals
    loc_totals = (
        db.query(
            Location.display_name.label("location"),
            func.sum(DailySales.quantity).label("total"),
        )
        .join(Location, DailySales.location_id == Location.id)
        .filter(DailySales.sale_date >= start_date)
        .group_by(Location.display_name)
        .order_by(func.sum(DailySales.quantity).desc())
        .all()
    )

    # Per flavor totals
    flavor_totals = (
        db.query(
            Flavor.code,
            Flavor.name.label("flavor"),
            func.sum(DailySales.quantity).label("total"),
        )
        .join(Flavor, DailySales.flavor_id == Flavor.id)
        .filter(DailySales.sale_date >= start_date)
        .group_by(Flavor.code, Flavor.name)
        .order_by(func.sum(DailySales.quantity).desc())
        .all()
    )

    # Daily totals
    daily_totals = (
        db.query(
            DailySales.sale_date,
            func.sum(DailySales.quantity).label("total"),
        )
        .filter(DailySales.sale_date >= start_date)
        .group_by(DailySales.sale_date)
        .order_by(DailySales.sale_date)
        .all()
    )

    return {
        "period_days": days,
        "by_location": [{"location": r.location, "total": r.total} for r in loc_totals],
        "by_flavor": [{"code": r.code, "flavor": r.flavor, "total": r.total} for r in flavor_totals],
        "by_date": [{"date": str(r.sale_date), "total": r.total} for r in daily_totals],
    }


@router.get("/live-ops")
def get_live_ops(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Live Operations Center — all locations at a glance."""
    today = date.today()
    locations = db.query(Location).filter(Location.is_active.is_(True)).order_by(Location.sort_order).all()

    result = []
    for loc in locations:
        # Today's live sales
        inv_rows = db.query(Inventory).filter(
            Inventory.inventory_date == today, Inventory.location_id == loc.id
        ).all()
        total_live_sales = sum(r.live_sales for r in inv_rows)
        total_opening = sum((r.beginning_inventory + r.received_cookies) for r in inv_rows)
        total_closing = sum(r.closing_inventory for r in inv_rows)

        # Dispatch plan
        dispatched = db.query(func.sum(DispatchPlan.amount_to_send)).filter(
            DispatchPlan.plan_date == today, DispatchPlan.location_id == loc.id
        ).scalar() or 0

        # Pending 2nd delivery requests
        pending_requests = db.query(DeliveryRequest).filter(
            DeliveryRequest.request_date == today,
            DeliveryRequest.location_id == loc.id,
            DeliveryRequest.status == "pending",
        ).count()

        # Sell-through rate
        sell_through = round((total_live_sales / total_opening * 100), 1) if total_opening > 0 else 0

        # Low stock flavors
        low_stock = []
        for inv in inv_rows:
            remaining = (inv.beginning_inventory + inv.received_cookies) - inv.live_sales
            if remaining < 5 and remaining >= 0:
                flavor = db.query(Flavor).filter(Flavor.id == inv.flavor_id).first()
                if flavor:
                    low_stock.append({"flavor": flavor.name, "remaining": remaining})

        result.append({
            "location_id": loc.id,
            "location_name": loc.display_name,
            "live_sales": total_live_sales,
            "opening_stock": total_opening,
            "dispatched": dispatched,
            "sell_through_pct": sell_through,
            "pending_2nd_delivery": pending_requests,
            "low_stock_flavors": low_stock[:5],
            "status": "alert" if pending_requests > 0 or len(low_stock) > 2 else "ok",
        })

    return {"date": str(today), "locations": result}
