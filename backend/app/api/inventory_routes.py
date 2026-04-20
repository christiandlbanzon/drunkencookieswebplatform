from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import Inventory
from app.models.flavor import Flavor
from app.models.location import Location
from app.models.delivery_request import DeliveryRequest
from app.auth.dependencies import require_module, get_current_user
from app.models.user import User
from app.schemas.inventory import InventoryResponse, InventoryRow, InventoryUpdate
from app.services.sheets_sync import sync_inventory_to_sheets

router = APIRouter()


@router.get("/{inv_date}/{location_id}", response_model=InventoryResponse)
def get_inventory(
    inv_date: date,
    location_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_module("store")),
):
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    inv_rows = (
        db.query(Inventory)
        .filter(Inventory.inventory_date == inv_date, Inventory.location_id == location_id)
        .all()
    )
    inv_map = {r.flavor_id: r for r in inv_rows}

    rows = []
    for f in flavors:
        inv = inv_map.get(f.id)
        rows.append(InventoryRow(
            flavor_id=f.id,
            flavor_code=f.code,
            flavor_name=f.name,
            beginning_inventory=inv.beginning_inventory if inv else 0,
            sent_cookies=inv.sent_cookies if inv else 0,
            received_cookies=inv.received_cookies if inv else 0,
            opening_stock=(inv.beginning_inventory + inv.received_cookies) if inv else 0,
            live_sales=inv.live_sales if inv else 0,
            second_delivery=inv.second_delivery if inv else 0,
            closing_inventory=inv.closing_inventory if inv else 0,
            expired=inv.expired if inv and inv.expired else 0,
            flawed=inv.flawed if inv and inv.flawed else 0,
            used_as_display=inv.used_as_display if inv and inv.used_as_display else 0,
            given_away=inv.given_away if inv and inv.given_away else 0,
            production_waste=inv.production_waste if inv and inv.production_waste else 0,
        ))

    return InventoryResponse(
        inventory_date=inv_date,
        location_id=loc.id,
        location_name=loc.display_name,
        rows=rows,
    )


@router.patch("/{inv_date}/{location_id}/{flavor_id}")
def update_inventory(
    inv_date: date,
    location_id: int,
    flavor_id: int,
    body: InventoryUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_module("store")),
):
    inv = (
        db.query(Inventory)
        .filter(
            Inventory.inventory_date == inv_date,
            Inventory.location_id == location_id,
            Inventory.flavor_id == flavor_id,
        )
        .first()
    )
    if not inv:
        # Auto-create the row
        inv = Inventory(
            inventory_date=inv_date,
            location_id=location_id,
            flavor_id=flavor_id,
        )
        db.add(inv)

    if body.beginning_inventory is not None:
        inv.beginning_inventory = body.beginning_inventory
    if body.sent_cookies is not None:
        inv.sent_cookies = body.sent_cookies
    if body.received_cookies is not None:
        inv.received_cookies = body.received_cookies
    if body.second_delivery is not None:
        inv.second_delivery = body.second_delivery
    if body.closing_inventory is not None:
        inv.closing_inventory = body.closing_inventory
    if body.expired is not None:
        inv.expired = body.expired
    if body.flawed is not None:
        inv.flawed = body.flawed
    if body.used_as_display is not None:
        inv.used_as_display = body.used_as_display
    if body.given_away is not None:
        inv.given_away = body.given_away
    if body.production_waste is not None:
        inv.production_waste = body.production_waste
    inv.synced_to_sheets = False
    db.commit()
    # NOTE: Do NOT sync to Mall PARs sheet — staff sometimes enter formulas
    # in Beginning Inventory (e.g. "=9+9" for multiple receipts). Writing
    # a plain number would destroy those formulas.

    # Validation warnings (don't block save, just inform)
    warnings = []
    opening = (inv.beginning_inventory or 0) + (inv.received_cookies or 0)
    live = inv.live_sales or 0
    closing = inv.closing_inventory or 0
    expected = opening - live
    if expected < 0 and opening > 0:
        warnings.append(f"Live sales ({live}) exceed opening stock ({opening}). Check beginning inventory or received cookies.")
    if closing > opening + (inv.second_delivery or 0) and opening > 0:
        warnings.append(f"Closing ({closing}) is higher than opening ({opening}) + 2nd delivery ({inv.second_delivery or 0}). Was a delivery missed?")
    return {"status": "ok", "warnings": warnings}


@router.post("/delivery-request/{location_id}")
def create_delivery_request(
    location_id: int,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Store manager requests a 2nd delivery."""
    req = DeliveryRequest(
        request_date=date.today(),
        location_id=location_id,
        requested_by=current_user.display_name,
        notes=notes,
        status="pending",
    )
    db.add(req)
    db.commit()

    # Notify dispatch team
    from app.api.notifications_routes import create_notification
    loc = db.query(Location).filter(Location.id == location_id).first()
    loc_name = loc.display_name if loc else f"Location {location_id}"
    create_notification(
        db,
        kind="delivery_request",
        severity="warning",
        title=f"2nd Delivery Requested — {loc_name}",
        body=f"{current_user.display_name} requested a 2nd delivery. {notes}".strip(),
        target_role="dispatch",
        link_url="/dispatch",
    )
    # Also notify ops_manager and admin
    create_notification(
        db, kind="delivery_request", severity="warning",
        title=f"2nd Delivery Requested — {loc_name}",
        body=f"{current_user.display_name} requested a 2nd delivery. {notes}".strip(),
        target_role="ops_manager", link_url="/dispatch",
    )

    return {"status": "ok", "request_id": req.id}


@router.get("/delivery-requests")
def list_delivery_requests(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """List today's delivery requests (for dispatch view)."""
    query = db.query(DeliveryRequest).filter(DeliveryRequest.request_date == date.today())
    if status_filter:
        query = query.filter(DeliveryRequest.status == status_filter)
    requests = query.order_by(DeliveryRequest.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "location_id": r.location_id,
            "requested_by": r.requested_by,
            "status": r.status,
            "notes": r.notes,
            "created_at": str(r.created_at),
        }
        for r in requests
    ]


@router.patch("/delivery-request/{request_id}/status")
def update_delivery_request_status(
    request_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    _=Depends(require_module("dispatch")),
):
    """Dispatch updates request status (accepted/completed/rejected)."""
    req = db.query(DeliveryRequest).filter(DeliveryRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = new_status
    db.commit()
    return {"status": "ok"}
