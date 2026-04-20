"""
Google Sheets reader — pulls closing inventory from the Mall PARs sheet.
Used to get real inventory data for PAR calculations.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.flavor import Flavor
from app.services.sheets_sync import _get_sheets_service, _get_tab_name, MALL_PARS_LOCATION_START_COL, MALL_PARS_FLAVOR_START_ROW, _col_offset

logger = logging.getLogger(__name__)
settings = get_settings()


def read_closing_inventory_from_sheets(db: Session, inv_date: date) -> dict:
    """
    Read closing inventory from the Mall PARs Google Sheet for all locations.
    Updates inventory.closing_inventory in the database.
    Returns summary.
    """
    service = _get_sheets_service()
    if not service:
        return {"error": "Cannot connect to Google Sheets"}

    tab = _get_tab_name(inv_date)
    sheet_id = settings.MALL_PARS_SHEET_ID

    locations = db.query(Location).filter(Location.is_active.is_(True)).order_by(Location.sort_order).all()
    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True), Flavor.category == "cookie").order_by(Flavor.sort_order).all()

    updated = 0

    for loc in locations:
        start_col = MALL_PARS_LOCATION_START_COL.get(loc.name)
        if not start_col:
            continue

        # Closing inventory is not a specific column in the 6-column block
        # but typically the remaining stock at end of day.
        # We read the "Beginning Inventory" column (col 1) as a proxy for next day's closing.
        # The actual closing would be manually entered.
        # For now, read all 6 columns and use what's available.
        start_row = MALL_PARS_FLAVOR_START_ROW
        end_row = start_row + len(flavors) - 1
        end_col = _col_offset(start_col, 5)  # 6 columns

        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f"'{tab}'!{start_col}{start_row}:{end_col}{end_row}",
            ).execute()

            values = result.get("values", [])

            for i, flav in enumerate(flavors):
                if i >= len(values):
                    break
                row = values[i]
                # Column layout: Begin, Sent, Received, Opening, LiveSales, 2ndDelivery
                begin = int(row[0]) if len(row) > 0 and row[0] else 0
                sent = int(row[1]) if len(row) > 1 and row[1] else 0
                received = int(row[2]) if len(row) > 2 and row[2] else 0
                live_sales = int(row[4]) if len(row) > 4 and row[4] else 0

                # Upsert inventory
                inv = (
                    db.query(Inventory)
                    .filter(
                        Inventory.inventory_date == inv_date,
                        Inventory.location_id == loc.id,
                        Inventory.flavor_id == flav.id,
                    )
                    .first()
                )
                if inv:
                    inv.beginning_inventory = begin
                    inv.sent_cookies = sent
                    inv.received_cookies = received
                    inv.live_sales = live_sales
                else:
                    db.add(Inventory(
                        inventory_date=inv_date,
                        location_id=loc.id,
                        flavor_id=flav.id,
                        beginning_inventory=begin,
                        sent_cookies=sent,
                        received_cookies=received,
                        live_sales=live_sales,
                    ))
                updated += 1

            logger.info(f"Read inventory for {loc.name} on {inv_date}: {len(values)} rows")

        except Exception as e:
            logger.error(f"Failed to read inventory for {loc.name}: {e}")
            continue

    db.commit()
    return {"date": str(inv_date), "updated": updated}
