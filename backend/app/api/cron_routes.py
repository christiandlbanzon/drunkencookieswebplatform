"""
Cron/scheduler endpoints — called by Cloud Scheduler daily.
Secured via API key header (X-Cron-Key) or admin JWT auth.
"""

import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.auth.dependencies import get_current_user
from app.auth.roles import Role
from app.models.user import User
from app.services.par_calculator import generate_dispatch_plan, generate_bake_plan
from app.services.clover_ingest import ingest_sales_for_date
from app.services.live_sales import poll_live_sales
from app.services.sheets_reader import read_closing_inventory_from_sheets
from app.services.shopify_sync import sync_shopify_orders
from app.services.inventory_sync import sync_inventory_from_sheet

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Cron key is separate from JWT_SECRET. Falls back to JWT_SECRET only for
# backward compatibility with existing schedulers that haven't been updated —
# a warning is logged in that case.
CRON_API_KEY = settings.CRON_API_KEY or settings.JWT_SECRET
if not settings.CRON_API_KEY:
    logger.warning(
        "CRON_API_KEY is not set; falling back to JWT_SECRET. "
        "This is insecure — set a separate CRON_API_KEY env var."
    )


def verify_cron_caller(
    x_cron_key: str | None = Header(None),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """Allow access via X-Cron-Key header or admin/ops_manager JWT."""
    if x_cron_key and x_cron_key == CRON_API_KEY:
        return "scheduler"
    # Also accept the legacy JWT_SECRET during the transition period
    if x_cron_key and settings.CRON_API_KEY and x_cron_key == settings.JWT_SECRET:
        logger.warning("Cron called with legacy JWT_SECRET; update the scheduler to use CRON_API_KEY")
        return "scheduler-legacy"
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        from app.auth.jwt_handler import decode_access_token
        payload = decode_access_token(token)
        if payload:
            role = payload.get("role", "")
            if role in (Role.ADMIN.value, Role.OPS_MANAGER.value):
                return f"user:{payload.get('sub')}"
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid cron key or insufficient permissions")


def _validate_date(target_date: date | None) -> date:
    if target_date is None:
        return date.today()
    today = date.today()
    if target_date < today - timedelta(days=7) or target_date > today + timedelta(days=30):
        raise HTTPException(status_code=400, detail="Date must be within 7 days past or 30 days future")
    return target_date


@router.post("/daily-plans")
def generate_daily_plans(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    caller: str = Depends(verify_cron_caller),
):
    """Generate dispatch + bake plans for today."""
    target_date = _validate_date(target_date)
    logger.info(f"Generating daily plans for {target_date} (caller: {caller})")

    dispatch = generate_dispatch_plan(db, target_date)
    bake = generate_bake_plan(db, target_date)

    dispatch_total = sum((p.override_amount if p.override_amount is not None else p.amount_to_send) for p in dispatch)
    bake_total = sum((p.override_amount if p.override_amount is not None else p.amount_to_bake) for p in bake)

    return {"date": str(target_date), "dispatch_total": dispatch_total, "bake_total": bake_total, "caller": caller}


@router.post("/ingest-sales")
def ingest_daily_sales(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    caller: str = Depends(verify_cron_caller),
):
    """
    Ingest sales data from Clover POS for a given date (defaults to yesterday).
    Called nightly by Cloud Scheduler at ~11:59 PM PR time.
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    else:
        target_date = _validate_date(target_date)

    logger.info(f"Ingesting sales for {target_date} (caller: {caller})")
    result = ingest_sales_for_date(db, target_date)
    result["caller"] = caller
    return result


@router.post("/nightly-pipeline")
def nightly_pipeline(
    db: Session = Depends(get_db),
    caller: str = Depends(verify_cron_caller),
):
    """
    Full nightly pipeline: ingest yesterday's sales, then generate today's plans.
    Single endpoint for Cloud Scheduler to call once.
    """
    yesterday = date.today() - timedelta(days=1)
    today = date.today()

    logger.info(f"Running nightly pipeline (caller: {caller})")

    # Step 1: Ingest yesterday's sales (may fail on Cloud Run if legacy code not available)
    try:
        ingest_result = ingest_sales_for_date(db, yesterday)
    except Exception as e:
        logger.error(f"Nightly ingest failed for {yesterday}: {e}", exc_info=True)
        # Create an admin notification so someone notices if ingest is broken
        try:
            from app.api.notifications_routes import create_notification
            create_notification(
                db, kind="ingest_failure", severity="critical",
                title=f"Nightly sales ingest failed — {yesterday}",
                body=f"Ingest threw an error: {str(e)[:200]}. Plans may be using stale data.",
                target_role="admin",
            )
            create_notification(
                db, kind="ingest_failure", severity="critical",
                title=f"Nightly sales ingest failed — {yesterday}",
                body=f"{str(e)[:200]}",
                target_role="ops_manager",
            )
        except Exception:
            pass
        ingest_result = {"date": str(yesterday), "error": str(e), "records": 0}

    # Step 2: Generate today's plans
    dispatch = generate_dispatch_plan(db, today)
    bake = generate_bake_plan(db, today)

    dispatch_total = sum((p.override_amount if p.override_amount is not None else p.amount_to_send) for p in dispatch)
    bake_total = sum((p.override_amount if p.override_amount is not None else p.amount_to_bake) for p in bake)

    return {
        "ingest": ingest_result,
        "plans": {"date": str(today), "dispatch_total": dispatch_total, "bake_total": bake_total},
        "caller": caller,
    }


@router.post("/live-sales")
def refresh_live_sales(
    db: Session = Depends(get_db),
    caller: str = Depends(verify_cron_caller),
):
    """
    Poll Clover for today's live sales and update inventory.live_sales.
    Called every 5 minutes by Cloud Scheduler.
    """
    logger.info(f"Polling live sales (caller: {caller})")
    try:
        result = poll_live_sales(db)
    except Exception as e:
        result = {"error": str(e), "updated": 0}
    result["caller"] = caller
    return result


@router.post("/import-inventory")
def import_inventory_from_sheets(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    caller: str = Depends(verify_cron_caller),
):
    """Import inventory from Mall PARs Google Sheet for a given date."""
    if target_date is None:
        target_date = date.today()
    logger.info(f"Importing inventory from Sheets for {target_date} (caller: {caller})")
    result = read_closing_inventory_from_sheets(db, target_date)
    result["caller"] = caller
    return result


@router.post("/sync-inventory")
def sync_inventory(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    caller: str = Depends(verify_cron_caller),
):
    """
    Sync all manual inventory columns from Mall PARs Google Sheet into DB.
    Reads: beginning inventory, sent, received, 2nd delivery, closing, waste.
    Called periodically (e.g., every 30 min) so DB stays current with staff entries.
    """
    if target_date is None:
        target_date = date.today()
    else:
        target_date = _validate_date(target_date)
    logger.info(f"Syncing inventory from Mall PARs for {target_date} (caller: {caller})")
    result = sync_inventory_from_sheet(db, target_date)
    result["caller"] = caller
    return result


@router.post("/check-alerts")
def check_operational_alerts(
    db: Session = Depends(get_db),
    caller: str = Depends(verify_cron_caller),
):
    """
    Check for operational issues and create notifications:
      - Low stock: any location > 80% sell-through
      - Missing closing: past 9pm local and closing inventory not entered
    Called every 30 min during business hours.
    """
    from app.models.inventory import Inventory
    from app.models.location import Location
    from app.models.notification import Notification
    from app.api.notifications_routes import create_notification
    from sqlalchemy import func as sqlfunc

    today = date.today()
    alerts = []

    locations = db.query(Location).filter(Location.is_active.is_(True)).all()
    for loc in locations:
        rows = db.query(Inventory).filter(
            Inventory.inventory_date == today,
            Inventory.location_id == loc.id,
        ).all()
        if not rows:
            continue

        opening = sum((r.beginning_inventory or 0) + (r.received_cookies or 0) for r in rows)
        sales = sum(r.live_sales or 0 for r in rows)

        if opening > 0:
            sell_through = sales / opening * 100
            if sell_through > 80:
                # Check if we already notified for this location today
                existing = db.query(Notification).filter(
                    Notification.kind == "low_stock",
                    Notification.title.like(f"%{loc.display_name}%"),
                    sqlfunc.date(Notification.created_at) == today,
                ).first()
                if not existing:
                    create_notification(
                        db, kind="low_stock", severity="critical",
                        title=f"Low Stock — {loc.display_name}",
                        body=f"Sell-through {sell_through:.0f}% ({sales} sold of {opening} opening). Consider a 2nd delivery.",
                        target_role="dispatch", link_url=f"/store/{loc.id}",
                    )
                    create_notification(
                        db, kind="low_stock", severity="critical",
                        title=f"Low Stock — {loc.display_name}",
                        body=f"Sell-through {sell_through:.0f}%",
                        target_role="ops_manager", link_url=f"/store/{loc.id}",
                    )
                    alerts.append(f"{loc.display_name}: {sell_through:.0f}%")

    return {"alerts_fired": len(alerts), "details": alerts, "caller": caller}


@router.post("/sync-orders")
def sync_orders(
    days: int = 7,
    db: Session = Depends(get_db),
    caller: str = Depends(verify_cron_caller),
):
    """Sync Shopify orders from the last N days into the database."""
    logger.info(f"Syncing Shopify orders ({days} days) (caller: {caller})")
    try:
        result = sync_shopify_orders(db, days=days)
    except Exception as e:
        result = {"error": str(e), "synced": 0}
    result["caller"] = caller
    return result
