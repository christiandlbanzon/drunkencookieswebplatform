"""
Read closing inventory from the Mall PARs Google Sheet.

Mall PARs structure:
- Tabs: '4-1', '4-2', ..., '4-30'
- Row 1: Date + location names
- Row 2: Column headers
- Row 3+: Flavor data (A-N)

Per location block (14 columns + 1 blank separator):
  Col 1: Beginning Inventory
  Col 2: Sent Cookies
  Col 3: Received Cookies
  Col 4: Opening Stock (auto)
  Col 5: Live Sales Data
  Col 6: 2nd Delivery Sent
  Col 7: Expected Live Inventory (auto)
  Col 8: Ending Inventory  ← what we need
  Cols 9-14: Waste tracking
"""

import logging
from datetime import date

from app.config import get_settings
from app.services.sheets_sync import _get_sheets_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Location -> start column number (1-indexed) for Beginning Inventory
# Each block is 13 data cols + 1 blank separator = 14 cols apart
# Verified from Mall PARs sheet row 1 (location names)
MALL_PARS_LOCATION_START_COL = {
    "San Patricio": 2,      # B (B-N = 13 cols, O blank)
    "PlazaSol": 16,         # P (P-AB = 13 cols, AC blank)
    "Plaza del Sol": 16,
    "Montehiedra": 30,      # AD (AD-AP = 13 cols, AQ blank)
    "Plaza Carolina": 44,   # AR (AR-BD = 13 cols, BE blank)
    "Plaza": 58,            # BF (BF-BR = 13 cols, BS blank)
    "Plaza Las Americas": 58,
    "VSJ": 72,              # BT
    "Viejo San Juan": 72,
}

# Ending Inventory column offset within each location block
# Most locations: 13 cols, ending inv at offset 7 (column 8)
# VSJ (Old San Juan): 4 cols only, ending inv at offset 3 (column 4)
ENDING_INVENTORY_OFFSET_DEFAULT = 7
ENDING_INVENTORY_OFFSET_VSJ = 3

# Flavors are in rows 3-16 (A-N)
FLAVOR_START_ROW = 3

_cache: dict[str, dict[tuple[str, str], int]] = {}  # {tab: {(location, flavor_code): closing}}


def clear_inventory_cache():
    global _cache
    _cache = {}


def _col_num_to_letter(num: int) -> str:
    """Convert 1-indexed column number to letter (1=A, 27=AA)."""
    result = ""
    while num > 0:
        num -= 1
        result = chr(num % 26 + ord("A")) + result
        num //= 26
    return result


def _load_mall_pars_inventory(tab_name: str) -> dict[tuple[str, str], int]:
    """Load all closing inventory values from a Mall PARs tab."""
    if tab_name in _cache:
        return _cache[tab_name]

    service = _get_sheets_service()
    if not service:
        return {}

    sheet_id = settings.MALL_PARS_SHEET_ID
    flavor_codes = list("ABCDEFGHIJKLMN")
    end_row = FLAVOR_START_ROW + len(flavor_codes) - 1

    result_map: dict[tuple[str, str], int] = {}

    try:
        # Read each location's Ending Inventory column
        ranges = []
        loc_keys = []
        for loc_name, start_col in MALL_PARS_LOCATION_START_COL.items():
            # Skip duplicate aliases
            if loc_name in ("Plaza del Sol", "Plaza Las Americas", "Viejo San Juan"):
                continue
            offset = ENDING_INVENTORY_OFFSET_VSJ if loc_name == "VSJ" else ENDING_INVENTORY_OFFSET_DEFAULT
            ending_col = _col_num_to_letter(start_col + offset)
            ranges.append(f"'{tab_name}'!{ending_col}{FLAVOR_START_ROW}:{ending_col}{end_row}")
            loc_keys.append(loc_name)

        result = service.spreadsheets().values().batchGet(
            spreadsheetId=sheet_id,
            ranges=ranges,
        ).execute()

        for i, value_range in enumerate(result.get("valueRanges", [])):
            loc_name = loc_keys[i]
            values = value_range.get("values", [])
            for j, code in enumerate(flavor_codes):
                qty = 0
                if j < len(values) and values[j] and values[j][0]:
                    try:
                        qty = int(float(values[j][0]))
                    except (ValueError, TypeError):
                        qty = 0
                result_map[(loc_name, code)] = qty

        _cache[tab_name] = result_map
        logger.info(f"Loaded Mall PARs closing inventory from '{tab_name}' for {len(loc_keys)} locations")
        return result_map

    except Exception as e:
        logger.error(f"Failed to load Mall PARs '{tab_name}': {e}")
        return {}


def get_closing_inventory_from_sheet(
    location_name: str,
    flavor_code: str,
    target_date: date,
) -> int | None:
    """
    Read closing (Ending) inventory from Mall PARs sheet for a specific date/location/flavor.
    Returns the value from the sheet (including 0), or None if not found.
    """
    # Normalize location name
    loc_key = location_name
    if location_name == "Plaza Las Americas":
        loc_key = "Plaza"
    elif location_name == "Plaza del Sol":
        loc_key = "PlazaSol"
    elif location_name == "Viejo San Juan":
        loc_key = "VSJ"

    if flavor_code not in "ABCDEFGHIJKLMN":
        return None

    tab_name = f"{target_date.month}-{target_date.day}"
    cache = _load_mall_pars_inventory(tab_name)
    return cache.get((loc_key, flavor_code))  # None if not loaded
