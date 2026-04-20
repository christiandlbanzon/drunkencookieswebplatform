"""
Dual-write service: keeps Google Sheets in sync with the platform database
during the transition period.

This ensures the existing Mall PARs, Dispatch PARs, and Morning PARs sheets
continue to be updated so staff who haven't migrated to the web app can still
use the spreadsheets.

Requires: GOOGLE_SERVICE_ACCOUNT_FILE and DUAL_WRITE_ENABLED=true in .env
"""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.dispatch import DispatchPlan
from app.models.bake_plan import BakePlan
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.flavor import Flavor

logger = logging.getLogger(__name__)
settings = get_settings()

# Dispatch PARs: 5 locations stacked vertically, 18 rows each
DISPATCH_LOCATION_START_ROWS = {
    "San Patricio": 2,
    "PlazaSol": 20,
    "Montehiedra": 38,
    "Plaza Carolina": 56,
    "Plaza": 74,
}

def _get_sheets_service():
    """Build Google Sheets API service using service account credentials."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return build("sheets", "v4", credentials=creds)
    except Exception as e:
        logger.error(f"Failed to create Sheets service: {e}")
        return None


def _get_tab_name(target_date: date) -> str:
    """Convert date to sheet tab name like '4-9' for April 9."""
    return f"{target_date.month}-{target_date.day}"


def sync_dispatch_to_sheets(db: Session, plan_date: date) -> bool:
    """
    Write dispatch plan data to the Dispatch PARs Google Sheet.

    Writes columns B-F for each location block in the day's tab.
    """
    if not settings.DUAL_WRITE_ENABLED:
        return False

    service = _get_sheets_service()
    if not service:
        return False

    tab = _get_tab_name(plan_date)
    sheet_id = settings.DISPATCH_PARS_SHEET_ID

    locations = db.query(Location).filter(Location.is_active.is_(True)).order_by(Location.sort_order).all()
    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()

    batch_data = []

    for loc in locations:
        start_row = DISPATCH_LOCATION_START_ROWS.get(loc.name)
        if start_row is None:
            continue

        plans = (
            db.query(DispatchPlan)
            .filter(DispatchPlan.plan_date == plan_date, DispatchPlan.location_id == loc.id)
            .all()
        )
        plan_map = {p.flavor_id: p for p in plans}

        rows = []
        for flav in flavors:
            p = plan_map.get(flav.id)
            if p:
                rows.append([
                    float(p.sales_trend_median),
                    float(p.par_value),
                    p.adjusted_par,
                    p.live_inventory,
                    p.override_amount if p.override_amount is not None else p.amount_to_send,
                ])
            else:
                rows.append([0, 0, 0, 0, 0])

        end_row = start_row + len(rows) - 1
        batch_data.append({
            "range": f"'{tab}'!B{start_row}:F{end_row}",
            "values": rows,
        })

    try:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": batch_data,
            },
        ).execute()

        # Mark as synced
        db.query(DispatchPlan).filter(
            DispatchPlan.plan_date == plan_date,
            DispatchPlan.synced_to_sheets.is_(False),
        ).update({"synced_to_sheets": True})
        db.commit()

        logger.info(f"Synced dispatch plan for {plan_date} to Sheets")
        return True

    except Exception as e:
        logger.error(f"Failed to sync dispatch to Sheets: {e}")
        return False


def sync_bake_to_sheets(db: Session, plan_date: date) -> bool:
    """
    Write bake plan data to the Morning PARs Google Sheet.

    Writes columns B, D, E, F, G, H, I for the day's tab.
    """
    if not settings.DUAL_WRITE_ENABLED:
        return False

    service = _get_sheets_service()
    if not service:
        return False

    tab = _get_tab_name(plan_date)
    sheet_id = settings.MORNING_PARS_SHEET_ID

    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    plans = db.query(BakePlan).filter(BakePlan.plan_date == plan_date).all()
    plan_map = {p.flavor_id: p for p in plans}

    # Morning PARs layout: rows 3-16 (flavors A-N), cols B,D,E,F,G,H,I
    rows_b = []  # Col B: Amount to Bake
    rows_defghi = []  # Cols D-I

    for flav in flavors:
        p = plan_map.get(flav.id)
        if p:
            bake = p.override_amount if p.override_amount is not None else p.amount_to_bake
            rows_b.append([bake])
            rows_defghi.append([
                p.website_demand,
                p.missing_for_malls,
                p.closing_inv_yesterday,
                float(p.mall_forecast),
                float(p.sales_trend_median),
                p.total_projection,
            ])
        else:
            rows_b.append([0])
            rows_defghi.append([0, 0, 0, 0, 0, 0])

    start_row = 3
    end_row = start_row + len(rows_b) - 1

    try:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": f"'{tab}'!B{start_row}:B{end_row}", "values": rows_b},
                    {"range": f"'{tab}'!D{start_row}:I{end_row}", "values": rows_defghi},
                ],
            },
        ).execute()

        db.query(BakePlan).filter(
            BakePlan.plan_date == plan_date,
            BakePlan.synced_to_sheets.is_(False),
        ).update({"synced_to_sheets": True})
        db.commit()

        logger.info(f"Synced bake plan for {plan_date} to Sheets")
        return True

    except Exception as e:
        logger.error(f"Failed to sync bake to Sheets: {e}")
        return False


# Mall PARs: location blocks side by side, 6 columns each
# Columns: Begin Inv, Sent, Received, Opening (auto), Live Sales, 2nd Delivery
# Start columns per location (0-indexed, converted to A1 notation)
# From SYSTEM_OVERVIEW: San Patricio → PlazaSol → Montehiedra → Plaza Carolina → Plaza → VSJ
MALL_PARS_LOCATION_START_COL = {
    "San Patricio": "B",     # B-G
    "PlazaSol": "H",         # H-M
    "Montehiedra": "N",      # N-S
    "Plaza Carolina": "T",   # T-Y
    "Plaza": "Z",            # Z-AE
    "VSJ": "AF",             # AF-AK
}
MALL_PARS_FLAVOR_START_ROW = 6  # Flavors A-N start at row 6, 14 rows


def _col_offset(start_col: str, offset: int) -> str:
    """Get column letter offset from a start column. E.g. 'B'+2='D', 'Z'+1='AA'."""
    # Convert column letter to number
    num = 0
    for c in start_col:
        num = num * 26 + (ord(c) - ord('A') + 1)
    num += offset
    # Convert back to letter
    result = ""
    while num > 0:
        num -= 1
        result = chr(num % 26 + ord('A')) + result
        num //= 26
    return result


def sync_inventory_to_sheets(db: Session, inv_date: date, location_id: int) -> bool:
    """
    Write inventory data to the Mall PARs Google Sheet for a specific location.
    Each location block has 6 columns: Begin, Sent, Received, Opening, LiveSales, 2ndDelivery
    """
    if not settings.DUAL_WRITE_ENABLED:
        return False

    service = _get_sheets_service()
    if not service:
        return False

    tab = _get_tab_name(inv_date)
    sheet_id = settings.MALL_PARS_SHEET_ID

    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        return False

    start_col = MALL_PARS_LOCATION_START_COL.get(loc.name)
    if not start_col:
        logger.warning(f"Location '{loc.name}' not mapped in Mall PARs column layout")
        return False

    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    inv_rows = (
        db.query(Inventory)
        .filter(Inventory.inventory_date == inv_date, Inventory.location_id == location_id)
        .all()
    )
    inv_map = {r.flavor_id: r for r in inv_rows}

    # Build rows: each row = [begin, sent, received, opening(skip), live_sales, 2nd_delivery]
    # We write columns 1,2,3 (begin/sent/received) and column 6 (2nd delivery)
    # Columns 4 (opening) and 5 (live sales) are auto-calculated / auto-populated
    rows_manual = []  # Cols 1,2,3: Begin, Sent, Received
    rows_2nd = []     # Col 6: 2nd Delivery

    for flav in flavors:
        inv = inv_map.get(flav.id)
        if inv:
            rows_manual.append([inv.beginning_inventory, inv.sent_cookies, inv.received_cookies])
            rows_2nd.append([inv.second_delivery])
        else:
            rows_manual.append([0, 0, 0])
            rows_2nd.append([0])

    start_row = MALL_PARS_FLAVOR_START_ROW
    end_row = start_row + len(rows_manual) - 1
    col_begin = start_col
    col_received = _col_offset(start_col, 2)  # +2 for 3rd column
    col_2nd = _col_offset(start_col, 5)       # +5 for 6th column

    try:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {
                        "range": f"'{tab}'!{col_begin}{start_row}:{col_received}{end_row}",
                        "values": rows_manual,
                    },
                    {
                        "range": f"'{tab}'!{col_2nd}{start_row}:{col_2nd}{end_row}",
                        "values": rows_2nd,
                    },
                ],
            },
        ).execute()

        db.query(Inventory).filter(
            Inventory.inventory_date == inv_date,
            Inventory.location_id == location_id,
            Inventory.synced_to_sheets.is_(False),
        ).update({"synced_to_sheets": True})
        db.commit()

        logger.info(f"Synced inventory for {loc.name} on {inv_date} to Sheets")
        return True

    except Exception as e:
        logger.error(f"Failed to sync inventory for {loc.name} to Sheets: {e}")
        return False
