"""
Read 4-week medians directly from the Dispatch PARs Google Sheet.
This gives exact match with the sheet's own calculations.

When the platform has 4+ weeks of its own data, it computes locally instead.
"""

import logging
from datetime import date

from app.config import get_settings
from app.services.sheets_sync import _get_sheets_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Location -> (start_row of median column B)
# From Dispatch PARs sheet: 5 locations stacked, 18 rows each
DISPATCH_LOCATION_ROWS = {
    "San Patricio": 3,      # B3:B16
    "PlazaSol": 21,         # B21:B34
    "Montehiedra": 39,      # B39:B52
    "Plaza Carolina": 57,   # B57:B70
    "Plaza": 75,            # B75:B88
}

# Flavor code -> row offset (0-based within location block)
FLAVOR_OFFSETS = {
    "A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6,
    "H": 7, "I": 8, "J": 9, "K": 10, "L": 11, "M": 12, "N": 13,
}

# Cache per plan generation
_dispatch_cache: dict[str, list[float]] = {}


def clear_sheet_cache():
    """Clear the cache (call at start of plan generation)."""
    global _dispatch_cache
    _dispatch_cache = {}


def _load_dispatch_medians(tab_name: str) -> dict[str, list[float]]:
    """Load all location medians from the Dispatch PARs sheet for a given day tab."""
    if _dispatch_cache:
        return _dispatch_cache

    service = _get_sheets_service()
    if not service:
        return {}

    sheet_id = settings.DISPATCH_PARS_SHEET_ID

    try:
        # Read column B (medians) for all locations in one batch
        ranges = []
        loc_names = []
        for loc_name, start_row in DISPATCH_LOCATION_ROWS.items():
            end_row = start_row + 13  # 14 flavors
            ranges.append(f"'{tab_name}'!B{start_row}:B{end_row}")
            loc_names.append(loc_name)

        result = service.spreadsheets().values().batchGet(
            spreadsheetId=sheet_id,
            ranges=ranges,
        ).execute()

        for i, value_range in enumerate(result.get("valueRanges", [])):
            values = value_range.get("values", [])
            medians = []
            for row in values:
                try:
                    medians.append(float(row[0]) if row and row[0] else 0.0)
                except (ValueError, IndexError):
                    medians.append(0.0)
            _dispatch_cache[loc_names[i]] = medians

        logger.info(f"Loaded dispatch medians from sheet tab '{tab_name}' for {len(_dispatch_cache)} locations")
        return _dispatch_cache

    except Exception as e:
        logger.error(f"Failed to load dispatch medians from sheet: {e}")
        return {}


def compute_median_from_sheet(
    location_name: str,
    flavor_code: str,
    target_date: date,
    weeks: int = 4,
) -> tuple[float, int]:
    """
    Read the pre-computed median from the Dispatch PARs sheet.
    The sheet already computes the 4-week 2-day-sum median via its formula.
    We just read the result.

    Returns (median_value, data_points_count).
    data_points is always 4 (we trust the sheet's calculation).
    """
    # Map location names
    loc_key = location_name
    if location_name == "Plaza Las Americas":
        loc_key = "Plaza"
    elif location_name == "Plaza del Sol":
        loc_key = "PlazaSol"
    elif location_name == "Viejo San Juan":
        loc_key = "VSJ"

    if loc_key not in DISPATCH_LOCATION_ROWS:
        return 0.0, 0

    offset = FLAVOR_OFFSETS.get(flavor_code)
    if offset is None:
        return 0.0, 0

    tab_name = f"{target_date.month}-{target_date.day}"
    cache = _load_dispatch_medians(tab_name)

    medians = cache.get(loc_key, [])
    if offset >= len(medians):
        return 0.0, 0

    val = medians[offset]
    return val, 4 if val > 0 else 0
