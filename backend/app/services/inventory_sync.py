"""
Sync manual inventory data from Mall PARs Google Sheet into our DB.

Reads the green (staff-entered) columns for all locations/flavors:
  - Beginning Inventory (offset 0)
  - Sent Cookies (offset 1)
  - Received Cookies (offset 2)
  - 2nd Delivery Sent (offset 5)
  - Ending Inventory (offset 7, VSJ offset 3)
  - Waste: Expired(8), Flawed(9), Display(10), Given Away(11), Production(12)

Auto-calculated columns (Opening Stock, Live Sales, Expected) are NOT synced
— we compute those ourselves or get live sales from Clover.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.inventory import Inventory
from app.models.flavor import Flavor
from app.models.location import Location
from app.services.sheets_sync import _get_sheets_service
from app.services.mall_pars_reader import (
    MALL_PARS_LOCATION_START_COL,
    FLAVOR_START_ROW,
    _col_num_to_letter,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Column offsets within each 13-col location block (0-indexed from start_col)
# Regular locations (San Patricio, PlazaSol, Montehiedra, Plaza Carolina, Plaza)
REGULAR_OFFSETS = {
    "beginning_inventory": 0,
    "sent_cookies": 1,
    "received_cookies": 2,
    # 3 = Opening Stock (auto)
    # 4 = Live Sales (auto)
    "second_delivery": 5,
    # 6 = Expected Live Inventory (auto)
    "closing_inventory": 7,
    "expired": 8,
    "flawed": 9,
    "used_as_display": 10,
    "given_away": 11,
    "production_waste": 12,
}

# VSJ has a different layout — only 4 data columns
# Opening Inventory | Live Sales | Expected | Ending Inventory
VSJ_OFFSETS = {
    "beginning_inventory": 0,  # "Opening Inventory after cookies sent to Malls"
    "closing_inventory": 3,    # "Ending Inventory"
}

# Canonical location names (skip aliases)
SYNC_LOCATIONS = ["San Patricio", "PlazaSol", "Montehiedra", "Plaza Carolina", "Plaza", "VSJ"]


def sync_inventory_from_sheet(db: Session, target_date: date) -> dict:
    """
    Read all manual inventory columns from Mall PARs sheet for target_date
    and upsert into our inventory table.

    Returns summary of what was synced.
    """
    service = _get_sheets_service()
    if not service:
        return {"error": "Cannot connect to Google Sheets", "synced": 0}

    sheet_id = settings.MALL_PARS_SHEET_ID
    tab_name = f"{target_date.month}-{target_date.day}"

    # Load flavor + location maps
    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    flavor_codes = [f.code for f in flavors if f.code in "ABCDEFGHIJKLMN"]
    flavor_id_map = {f.code: f.id for f in flavors}

    locations = db.query(Location).filter(Location.is_active.is_(True)).all()
    loc_id_map = {loc.name: loc.id for loc in locations}
    # Add aliases
    loc_id_map["PlazaSol"] = loc_id_map.get("Plaza del Sol", loc_id_map.get("PlazaSol"))
    loc_id_map["Plaza"] = loc_id_map.get("Plaza Las Americas", loc_id_map.get("Plaza"))
    loc_id_map["VSJ"] = loc_id_map.get("Viejo San Juan", loc_id_map.get("VSJ"))

    end_row = FLAVOR_START_ROW + len(flavor_codes) - 1

    # Build batch ranges — read each location's full block at once
    ranges = []
    range_loc_keys = []

    for loc_name in SYNC_LOCATIONS:
        start_col = MALL_PARS_LOCATION_START_COL.get(loc_name)
        if not start_col:
            continue

        if loc_name == "VSJ":
            # VSJ: 4 columns only
            col_start = _col_num_to_letter(start_col)
            col_end = _col_num_to_letter(start_col + 3)
        else:
            # Regular: 13 columns
            col_start = _col_num_to_letter(start_col)
            col_end = _col_num_to_letter(start_col + 12)

        ranges.append(f"'{tab_name}'!{col_start}{FLAVOR_START_ROW}:{col_end}{end_row}")
        range_loc_keys.append(loc_name)

    try:
        result = service.spreadsheets().values().batchGet(
            spreadsheetId=sheet_id,
            ranges=ranges,
        ).execute()
    except Exception as e:
        logger.error(f"Failed to read Mall PARs sheet: {e}")
        return {"error": str(e), "synced": 0}

    synced = 0
    warnings = []

    for i, value_range in enumerate(result.get("valueRanges", [])):
        loc_name = range_loc_keys[i]
        loc_id = loc_id_map.get(loc_name)
        if not loc_id:
            continue

        offsets = VSJ_OFFSETS if loc_name == "VSJ" else REGULAR_OFFSETS
        rows = value_range.get("values", [])

        for j, code in enumerate(flavor_codes):
            if j >= len(rows):
                break

            row = rows[j]
            flavor_id = flavor_id_map.get(code)
            if not flavor_id:
                continue

            # Parse values from sheet row using offsets
            def get_val(offset):
                if offset < len(row) and row[offset]:
                    try:
                        return int(float(row[offset]))
                    except (ValueError, TypeError):
                        return 0
                return 0

            # Upsert inventory record
            inv = (
                db.query(Inventory)
                .filter(
                    Inventory.inventory_date == target_date,
                    Inventory.location_id == loc_id,
                    Inventory.flavor_id == flavor_id,
                )
                .first()
            )
            if not inv:
                inv = Inventory(
                    inventory_date=target_date,
                    location_id=loc_id,
                    flavor_id=flavor_id,
                )
                db.add(inv)

            # Update fields that exist in this location's layout
            for field_name, offset in offsets.items():
                val = get_val(offset)
                setattr(inv, field_name, val)

            # For VSJ, also try to parse sent_cookies from column C of the sheet
            # (not in the 4-col VSJ block — VSJ doesn't track sent/received the same way)

            synced += 1

    db.commit()
    logger.info(f"Synced {synced} inventory records from Mall PARs '{tab_name}'")
    return {"date": str(target_date), "synced": synced, "warnings": warnings}
