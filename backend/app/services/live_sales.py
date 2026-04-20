"""
Live sales polling service.
Fetches today's sales from Clover POS for each location
and updates both:
1. inventory.live_sales in the database
2. Mall PARs Google Sheet Live Sales column (dual-write)
"""

import logging
from datetime import date, datetime
from collections import defaultdict

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.flavor import Flavor
from app.services.clover_ingest import _setup_legacy_imports, match_flavor_id, LOCATION_NAME_TO_ID
from app.services.sheets_sync import (
    _get_sheets_service, _get_tab_name,
    MALL_PARS_LOCATION_START_COL, MALL_PARS_FLAVOR_START_ROW, _col_offset,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Location name -> DB name (for sheet column lookup)
LOCATION_ID_TO_NAME = {v: k for k, v in {
    "San Patricio": 1, "PlazaSol": 2, "VSJ": 3,
    "Montehiedra": 4, "Plaza": 5, "Plaza Carolina": 6,
}.items()}


def _write_live_sales_to_sheet(target_date: date, agg: dict, db: Session):
    """Write live sales to the Mall PARs Google Sheet (column 5 per location block)."""
    if not settings.DUAL_WRITE_ENABLED:
        return False

    service = _get_sheets_service()
    if not service:
        logger.warning("Cannot connect to Sheets for live sales dual-write")
        return False

    tab = _get_tab_name(target_date)
    sheet_id = settings.MALL_PARS_SHEET_ID

    locations = db.query(Location).filter(Location.is_active.is_(True)).order_by(Location.sort_order).all()
    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True), Flavor.category == "cookie").order_by(Flavor.sort_order).all()

    batch_data = []

    for loc in locations:
        start_col = MALL_PARS_LOCATION_START_COL.get(loc.name)
        if not start_col:
            continue

        # Live Sales is column 5 (0-indexed: offset 4)
        live_col = _col_offset(start_col, 4)
        start_row = MALL_PARS_FLAVOR_START_ROW

        rows = []
        for flav in flavors:
            qty = agg.get((loc.id, flav.id), 0)
            rows.append([qty])

        end_row = start_row + len(rows) - 1
        batch_data.append({
            "range": f"'{tab}'!{live_col}{start_row}:{live_col}{end_row}",
            "values": rows,
        })

    if not batch_data:
        return False

    try:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": batch_data},
        ).execute()
        logger.info(f"Live sales dual-written to Mall PARs sheet for {target_date}")
        return True
    except Exception as e:
        logger.error(f"Failed to write live sales to sheet: {e}")
        return False


def poll_live_sales(db: Session, target_date: date | None = None) -> dict:
    """
    Fetch today's live sales from Clover for all locations.
    Updates inventory.live_sales in DB + Mall PARs Google Sheet.
    """
    if target_date is None:
        target_date = date.today()

    deploy_dir = _setup_legacy_imports()
    if not deploy_dir:
        return {"error": "Legacy code not available"}

    import os
    original_cwd = os.getcwd()
    os.chdir(str(deploy_dir))

    try:
        import json as _json
        from pathlib import Path as _Path
        from src.fetch_clover_data import CloverDataFetcher
        from src.transform_data import DataTransformer

        target_dt = datetime.combine(target_date, datetime.min.time())

        # CLOVER ONLY — do NOT include Shopify for live store sales
        merchants_file = deploy_dir / "config" / "merchants.json"
        if not merchants_file.exists():
            return {"date": str(target_date), "error": "merchants.json not found", "updated": 0}

        merchants = _json.loads(merchants_file.read_text())
        all_orders = []
        for merchant in merchants:
            try:
                fetcher = CloverDataFetcher(merchant_id=merchant["id"], api_token=merchant["token"])
                orders = fetcher.fetch_orders_for_date(target_dt, location_name=merchant["name"])
                all_orders.extend(orders)
            except Exception as e:
                logger.warning(f"Failed to fetch from {merchant['name']}: {e}")

        if not all_orders:
            return {"date": str(target_date), "orders": 0, "updated": 0, "sheet_synced": False}

        transformer = DataTransformer()
        item_sales = transformer.extract_item_sales(all_orders, target_dt)
        cookie_sales = item_sales.get("Cookies", [])

        # Aggregate by (location_id, flavor_id)
        agg = defaultdict(int)
        for sale in cookie_sales:
            loc_id = LOCATION_NAME_TO_ID.get(sale.get("Location", ""))
            if not loc_id:
                continue
            flavor_id = match_flavor_id(sale.get("Flavor Name", ""))
            if not flavor_id:
                continue
            agg[(loc_id, flavor_id)] += int(sale.get("Quantity Sold", 0))

        # Step 1: Update database
        updated = 0
        for (loc_id, flav_id), qty in agg.items():
            inv = (
                db.query(Inventory)
                .filter(
                    Inventory.inventory_date == target_date,
                    Inventory.location_id == loc_id,
                    Inventory.flavor_id == flav_id,
                )
                .first()
            )
            if inv:
                inv.live_sales = qty
            else:
                inv = Inventory(
                    inventory_date=target_date,
                    location_id=loc_id,
                    flavor_id=flav_id,
                    live_sales=qty,
                )
                db.add(inv)
            updated += 1

        db.commit()

        # NOTE: Dual-write to Mall PARs sheet is DISABLED.
        # The old inventory-updater Cloud Run Job already writes to col F
        # every 5 min — dual-writing would cause race conditions.
        # Our platform reads from the sheet when needed.
        sheet_synced = False

        logger.info(f"Live sales updated: {updated} DB records (sheet write disabled)")
        return {
            "date": str(target_date),
            "orders": len(orders),
            "updated": updated,
            "sheet_synced": sheet_synced,
        }

    except Exception as e:
        logger.error(f"Live sales poll failed: {e}", exc_info=True)
        return {"date": str(target_date), "error": str(e), "updated": 0}

    finally:
        os.chdir(original_cwd)
