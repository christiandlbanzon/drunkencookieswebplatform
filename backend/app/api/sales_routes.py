from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.daily_sales import DailySales
from app.models.flavor import Flavor
from app.models.location import Location
from app.auth.dependencies import get_current_user
from app.schemas.sales import DailySalesResponse, DailySalesRow, MedianResponse
from app.services.par_calculator import compute_four_week_median
from app.services.shopify_orders import fetch_website_orders

router = APIRouter()


@router.get("/{sale_date}", response_model=list[DailySalesResponse])
def get_sales_for_date(
    sale_date: date,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    locations = db.query(Location).filter(Location.is_active.is_(True)).order_by(Location.sort_order).all()
    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    flavor_map = {f.id: f for f in flavors}

    results = []
    for loc in locations:
        rows_db = (
            db.query(DailySales)
            .filter(DailySales.sale_date == sale_date, DailySales.location_id == loc.id)
            .all()
        )
        qty_map = {r.flavor_id: r for r in rows_db}
        rows = []
        for f in flavors:
            ds = qty_map.get(f.id)
            rows.append(DailySalesRow(
                flavor_id=f.id,
                flavor_code=f.code,
                flavor_name=f.name,
                quantity=ds.quantity if ds else 0,
                source=ds.source if ds else "none",
            ))
        results.append(DailySalesResponse(
            sale_date=sale_date,
            location_id=loc.id,
            location_name=loc.display_name,
            rows=rows,
        ))
    return results


@router.get("/{sale_date}/{location_id}", response_model=DailySalesResponse)
def get_sales_for_date_location(
    sale_date: date,
    location_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    rows_db = (
        db.query(DailySales)
        .filter(DailySales.sale_date == sale_date, DailySales.location_id == location_id)
        .all()
    )
    qty_map = {r.flavor_id: r for r in rows_db}
    rows = []
    for f in flavors:
        ds = qty_map.get(f.id)
        rows.append(DailySalesRow(
            flavor_id=f.id,
            flavor_code=f.code,
            flavor_name=f.name,
            quantity=ds.quantity if ds else 0,
            source=ds.source if ds else "none",
        ))
    return DailySalesResponse(
        sale_date=sale_date,
        location_id=loc.id,
        location_name=loc.display_name,
        rows=rows,
    )


@router.get("/median/{location_id}/{flavor_id}", response_model=MedianResponse)
def get_median(
    location_id: int,
    flavor_id: int,
    target_date: date | None = None,
    weeks: int = 4,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    if target_date is None:
        target_date = date.today()
    median_val, data_points = compute_four_week_median(db, location_id, flavor_id, target_date, weeks)
    return MedianResponse(
        location_id=location_id,
        flavor_id=flavor_id,
        median_value=median_val,
        weeks=weeks,
        data_points=data_points,
    )


@router.get("/website-orders/{target_date}")
def get_website_orders(
    target_date: date,
    _=Depends(get_current_user),
):
    """Fetch Shopify website orders split by time window."""
    return fetch_website_orders(target_date)
