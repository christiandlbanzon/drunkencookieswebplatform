"""
Read bake plan inputs directly from Google Sheets (VSJ-centric).

The Morning PARs sheet's bake formula is:
  B (Amount to bake) = MAX(0, I - F) + E
  where:
    E = Missing for Malls (manual)
    F = VSJ Ending Inventory yesterday (Mall PARs col BW)
    G = Mall Forecast (4-wk median of Dispatch PARs grand totals K98:K111)
    H = VSJ Sales Trend Median (Sales History VSJ tab)
    I = Total Projection = SUM(G+H) * (1 - reduction%)
"""

import logging
import statistics
from datetime import date, timedelta

from app.config import get_settings
from app.services.sheets_sync import _get_sheets_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Cache per generation
_bake_cache: dict[str, dict] = {}


def clear_bake_cache():
    global _bake_cache
    _bake_cache = {}


def get_bake_inputs_from_sheet(target_date: date) -> dict[str, dict]:
    """
    Read all bake plan inputs from the sheets for a given date.
    Returns: {flavor_code: {closing, forecast, median, total_proj, missing}}
    """
    cache_key = str(target_date)
    if cache_key in _bake_cache:
        return _bake_cache[cache_key]

    service = _get_sheets_service()
    if not service:
        return {}

    tab = f"{target_date.month}-{target_date.day}"
    morning_id = settings.MORNING_PARS_SHEET_ID

    try:
        # Read columns A (flavor name), B (bake), E (missing), F (closing), G (forecast), H (median), I (total proj)
        # Also read J3 for the reduction percentage
        result = service.spreadsheets().values().batchGet(
            spreadsheetId=morning_id,
            ranges=[f"'{tab}'!A3:I16", f"'{tab}'!J3"],
        ).execute()
        value_ranges = result.get("valueRanges", [])
        rows = value_ranges[0].get("values", []) if value_ranges else []

        # Parse reduction % from J3
        reduction_pct = 0.15  # default
        if len(value_ranges) > 1:
            j3_vals = value_ranges[1].get("values", [[]])
            if j3_vals and j3_vals[0]:
                try:
                    raw = str(j3_vals[0][0]).replace("%", "").strip()
                    reduction_pct = float(raw) / 100.0
                except (ValueError, TypeError):
                    pass

        result_map = {}
        for row in rows:
            if not row or not row[0]:
                continue
            name = row[0]
            if "[NOT IN USE]" in name:
                continue
            code = name[0] if name else None
            if code not in "ABCDEFGHIJKLMN":
                continue

            def safe_int(idx):
                try:
                    return int(float(row[idx])) if len(row) > idx and row[idx] else 0
                except (ValueError, TypeError):
                    return 0

            result_map[code] = {
                "amount_to_bake": safe_int(1),
                "missing_for_malls": safe_int(4),
                "closing_yesterday": safe_int(5),
                "mall_forecast": safe_int(6),
                "sales_trend_median": safe_int(7),
                "total_projection": safe_int(8),
            }

        result_map["_reduction_pct"] = reduction_pct
        _bake_cache[cache_key] = result_map
        logger.info(f"Loaded bake inputs from Morning PARs '{tab}' for {len(result_map)} flavors (reduction={reduction_pct*100:.0f}%)")
        return result_map

    except Exception as e:
        logger.error(f"Failed to load bake inputs from Morning PARs '{tab}': {e}")
        return {}
