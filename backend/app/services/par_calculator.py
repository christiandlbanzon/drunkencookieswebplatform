"""
PAR Calculator — replicates all Google Sheets formulas in Python.

Hybrid median: reads from Sales History Google Sheet when DB has < 4 weeks
of data, automatically switches to DB-computed median once enough data exists.

Formulas:
- 4-Week Median: 2-day-sum median (matches sheet formula exactly)
- Dispatch Col C: median * (1 - reduction_pct)
- Dispatch Col D: MAX(Col_C, minimum_par)
- Dispatch Col F: MAX(adjusted_par - live_inventory, 0)
- Bake Col B: MAX(0, total_projection - closing_inv_yesterday) + missing_for_malls
"""

import logging
import statistics
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.daily_sales import DailySales
from app.models.inventory import Inventory
from app.models.par_settings import ParSettings
from app.models.dispatch import DispatchPlan
from app.models.bake_plan import BakePlan
from app.models.flavor import Flavor
from app.models.location import Location

# Shared constants — single source of truth for flavor/location conventions
MALL_FLAVOR_CODES = "ABCDEFGHIJKLMN"  # flavors that go to malls (skip cookie shots)
VSJ_LOCATION_NAMES = ("VSJ", "Viejo San Juan", "Old San Juan")
PLAZA_LOCATION_NAMES = ("Plaza", "Plaza Las Americas")


def _get_vsj_location_id(db: Session) -> int:
    """Resolve VSJ's location ID by name (survives reseed)."""
    loc = db.query(Location).filter(Location.name.in_(VSJ_LOCATION_NAMES)).first()
    return loc.id if loc else 3  # fallback to historical ID


def compute_four_week_median(
    db: Session,
    location_id: int,
    flavor_id: int,
    target_date: date,
    weeks: int = 4,
) -> tuple[float, int]:
    """
    Compute the 4-week 2-day-sum median, matching the Google Sheet formula exactly.

    For each of 7, 14, 21, 28 days ago:
      - Sum that day + the next day's sales (2-day window)
    Filter out zero/missing values, then take MEDIAN of the remaining sums.
    If no data, return 0 (caller applies day-of-week fallback via minimum_par).

    Returns (median_value, data_points_count).
    """
    two_day_sums = []

    for w in range(1, weeks + 1):
        days_ago = w * 7
        day1 = target_date - timedelta(days=days_ago)
        day2 = day1 + timedelta(days=1)

        rows = (
            db.query(DailySales.sale_date, DailySales.quantity)
            .filter(
                DailySales.location_id == location_id,
                DailySales.flavor_id == flavor_id,
                DailySales.sale_date.in_([day1, day2]),
            )
            .all()
        )

        qty_map = {r.sale_date: r.quantity for r in rows}
        day1_qty = qty_map.get(day1, 0)
        day2_qty = qty_map.get(day2, 0)
        total = day1_qty + day2_qty

        if total > 0:
            two_day_sums.append(total)

    if not two_day_sums:
        return 0.0, 0
    return statistics.median(two_day_sums), len(two_day_sums)


def get_dow_fallback(
    db: Session,
    target_date: date,
    location_id: int,
    flavor_id: int,
    location_name: str = "",
) -> int:
    """
    Fallback values for new cookies with no sales history.
    Matches the Google Sheet formula:

    1. Thu/Fri/Sat/Sun → use standard table (per location)
    2. Mon/Tue/Wed → pull yesterday's actual sales first, then table default

    Standard table:
      VSJ:            Thu=48, Fri=48, Sat=48, Sun=48 (Mon-Wed default=48)
      Plaza:          Thu=30, Fri=30, Sat=30, Sun=20 (Mon-Wed default=15)
      Other malls:    Thu=15, Fri=15, Sat=10, Sun=5  (Mon-Wed default=10)
    """
    dow = target_date.strftime("%A")
    is_vsj = location_name in VSJ_LOCATION_NAMES
    is_plaza = location_name in PLAZA_LOCATION_NAMES

    # Standard table values
    if is_vsj:
        table = {"Thursday": 48, "Friday": 48, "Saturday": 48, "Sunday": 48}
        default = 48
    elif is_plaza:
        table = {"Thursday": 30, "Friday": 30, "Saturday": 30, "Sunday": 20}
        default = 15
    else:
        table = {"Thursday": 15, "Friday": 15, "Saturday": 10, "Sunday": 5}
        default = 10

    # Thu-Sun: use table directly
    if dow in ("Thursday", "Friday", "Saturday", "Sunday"):
        return table[dow]

    # Mon-Wed: try yesterday's actual sales first
    yesterday = target_date - timedelta(days=1)
    row = (
        db.query(DailySales.quantity)
        .filter(
            DailySales.location_id == location_id,
            DailySales.flavor_id == flavor_id,
            DailySales.sale_date == yesterday,
        )
        .first()
    )
    if row and row.quantity > 0:
        return row.quantity

    return default


def compute_dispatch_par(
    median_value: float,
    reduction_pct: float = 0.0,
    minimum_par: int = 10,
) -> tuple[float, int]:
    """
    Dispatch PARs columns C and D.

    Returns (par_raw, adjusted_par).
    """
    par_raw = median_value * (1 - reduction_pct)
    adjusted_par = max(int(round(par_raw)), minimum_par)
    return par_raw, adjusted_par


def compute_amount_to_send(adjusted_par: int, live_inventory: int) -> int:
    """Dispatch PARs Col F: MAX(adjusted_par - live_inventory, 0)."""
    return max(adjusted_par - live_inventory, 0)


def compute_amount_to_bake(
    total_projection: int,
    closing_inv_yesterday: int,
    missing_for_malls: int,
) -> int:
    """Morning PARs Col B: MAX(0, total_projection - closing_inv_yesterday) + missing_for_malls."""
    return max(0, total_projection - closing_inv_yesterday) + missing_for_malls


def get_par_settings_for_location(
    db: Session, location_id: int, target_date: date
) -> tuple[float, int, int]:
    """
    Get the effective PAR settings for a location on a given date.
    Falls back to defaults if no settings exist.

    Returns (reduction_pct, minimum_par, median_weeks).
    """
    row = (
        db.query(ParSettings)
        .filter(
            ParSettings.location_id == location_id,
            ParSettings.effective_date <= target_date,
        )
        .order_by(ParSettings.effective_date.desc())
        .first()
    )
    if row:
        return float(row.reduction_pct), row.minimum_par, row.median_weeks
    return 0.0, 10, 4


def get_previous_day_closing(
    db: Session, location_id: int, flavor_id: int, target_date: date,
    location_name: str = None, flavor_code: str = None,
) -> int:
    """
    Get closing inventory from the previous day for a location/flavor.
    Tries Mall PARs sheet first, falls back to DB.
    """
    prev_date = target_date - timedelta(days=1)

    # Try Mall PARs sheet first (authoritative source)
    if location_name and flavor_code:
        from app.services.mall_pars_reader import get_closing_inventory_from_sheet
        sheet_val = get_closing_inventory_from_sheet(location_name, flavor_code, prev_date)
        if sheet_val is not None:
            return sheet_val

    # Fall back to DB
    row = (
        db.query(Inventory.closing_inventory)
        .filter(
            Inventory.location_id == location_id,
            Inventory.flavor_id == flavor_id,
            Inventory.inventory_date == prev_date,
        )
        .first()
    )
    return row.closing_inventory if row else 0


def generate_dispatch_plan(db: Session, plan_date: date) -> list[DispatchPlan]:
    """
    Full dispatch calculation for all locations and flavors.

    Hybrid median: tries DB first, falls back to Sales History Google Sheet
    if DB has < 4 weeks of data. Automatically transitions to DB-only
    once enough data accumulates.
    """
    from app.services.sheets_median import compute_median_from_sheet, clear_sheet_cache
    from app.services.mall_pars_reader import clear_inventory_cache
    from app.services.transition_tracker import count_db_data_quality, log_transition_progress

    logger = logging.getLogger(__name__)
    clear_sheet_cache()  # Fresh sheet data each run
    clear_inventory_cache()  # Fresh inventory data each run

    # Log overall transition progress (Phase 1: log-only)
    log_transition_progress(db, plan_date)

    locations = db.query(Location).filter(Location.is_active.is_(True)).order_by(Location.sort_order).all()
    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    plans = []

    for loc in locations:
        reduction_pct, minimum_par, median_weeks = get_par_settings_for_location(db, loc.id, plan_date)
        is_plaza = loc.name in ("Plaza", "Plaza Las Americas")

        for flav in flavors:
            # Step 1: Compute median from our own DB (primary source)
            median_val, data_points = compute_four_week_median(db, loc.id, flav.id, plan_date, median_weeks)

            # Step 2: Fall back to Dispatch PARs sheet if DB has no data (new flavors)
            if data_points == 0 and flav.code in MALL_FLAVOR_CODES:
                sheet_median, sheet_points = compute_median_from_sheet(
                    loc.name, flav.code, plan_date, median_weeks
                )
                if sheet_points > 0:
                    median_val = sheet_median
                    data_points = sheet_points

            # Step 3: If still no data, use day-of-week fallback
            if data_points == 0:
                median_val = float(get_dow_fallback(db, plan_date, loc.id, flav.id, loc.name))

            par_raw, adjusted_par = compute_dispatch_par(median_val, reduction_pct, minimum_par)
            live_inv = get_previous_day_closing(db, loc.id, flav.id, plan_date, loc.name, flav.code)
            amount = compute_amount_to_send(adjusted_par, live_inv)

            # Upsert
            existing = (
                db.query(DispatchPlan)
                .filter(
                    DispatchPlan.plan_date == plan_date,
                    DispatchPlan.location_id == loc.id,
                    DispatchPlan.flavor_id == flav.id,
                )
                .first()
            )
            if existing:
                existing.sales_trend_median = Decimal(str(round(median_val, 2)))
                existing.par_value = Decimal(str(round(par_raw, 2)))
                existing.adjusted_par = adjusted_par
                existing.live_inventory = live_inv
                existing.amount_to_send = amount
                existing.synced_to_sheets = False
                plans.append(existing)
            else:
                plan = DispatchPlan(
                    plan_date=plan_date,
                    location_id=loc.id,
                    flavor_id=flav.id,
                    sales_trend_median=Decimal(str(round(median_val, 2))),
                    par_value=Decimal(str(round(par_raw, 2))),
                    adjusted_par=adjusted_par,
                    live_inventory=live_inv,
                    amount_to_send=amount,
                )
                db.add(plan)
                plans.append(plan)

    db.commit()
    return plans


def generate_bake_plan(db: Session, plan_date: date) -> list[BakePlan]:
    """
    VSJ-centric bake plan.

    Sources:
    - Sales Trend Median = VSJ 2-day-sum 4-week median from our DB
    - Closing Yesterday = VSJ Ending Inventory from Mall PARs sheet (staff enters there)
    - Mall Forecast = read from Morning PARs sheet (computed from past Dispatch PARs
      grand totals; requires historical dispatch data we don't yet have locally)
    - Missing for Malls = sum of dispatch amount_to_send across all 6 locations (DB)
    - Total Projection = (Forecast + Median) * (1 - 15%)
    - Bake = MAX(0, Projection - Closing) + Missing for Malls
    """
    from app.services.mall_pars_reader import get_closing_inventory_from_sheet, clear_inventory_cache
    from app.services.bake_sheet_reader import get_bake_inputs_from_sheet, clear_bake_cache

    clear_inventory_cache()
    clear_bake_cache()

    # Read Mall Forecast from Morning PARs sheet (4-week median of past Dispatch
    # grand totals — we don't have this history locally yet)
    sheet_bake = get_bake_inputs_from_sheet(plan_date)

    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()
    plans = []
    prev_date = plan_date - timedelta(days=1)

    vsj_location_id = _get_vsj_location_id(db)
    # Read reduction % from Morning PARs sheet (J3) — can change day to day
    REDUCTION_PCT = sheet_bake.get("_reduction_pct", 0.15)

    for flav in flavors:
        if flav.code not in MALL_FLAVOR_CODES:
            continue

        # Sales Trend Median = VSJ 2-day-sum median from our DB
        sales_trend_median, stm_points = compute_four_week_median(db, vsj_location_id, flav.id, plan_date)
        if stm_points == 0:
            # New cookie with no VSJ history — use VSJ day-of-week fallback
            sales_trend_median = float(get_dow_fallback(db, plan_date, vsj_location_id, flav.id, "VSJ"))

        # Mall Forecast = read from Morning PARs sheet (until we have history)
        sheet_data = sheet_bake.get(flav.code, {})
        mall_forecast = float(sheet_data.get("mall_forecast", 0))

        # Closing inventory = VSJ Ending Inventory from Mall PARs
        vsj_closing = get_closing_inventory_from_sheet("VSJ", flav.code, prev_date)
        total_closing = vsj_closing if vsj_closing is not None else 0

        # Fetch existing bake plan once (to preserve manual fields on regeneration)
        existing = (
            db.query(BakePlan)
            .filter(BakePlan.plan_date == plan_date, BakePlan.flavor_id == flav.id)
            .first()
        )

        # Missing for malls = 2nd-delivery shortfall (only populated later in day
        # when a mall runs out and VSJ doesn't have enough stock on hand).
        # At bake-planning time this is always 0. Staff can update it later
        # via the PATCH endpoint if a 2nd delivery is needed.
        missing_for_malls = 0

        # Website demand is also a manual field — preserve it.
        website_demand = existing.website_demand if (existing and existing.website_demand) else 0

        # Total Projection with 15% reduction (matches sheet)
        total_projection = int(round((mall_forecast + sales_trend_median) * (1 - REDUCTION_PCT)))

        # Amount to Bake
        amount_to_bake = max(0, total_projection - total_closing) + missing_for_malls

        if existing:
            existing.closing_inv_yesterday = total_closing
            existing.missing_for_malls = missing_for_malls
            existing.mall_forecast = Decimal(str(round(mall_forecast, 2)))
            existing.sales_trend_median = Decimal(str(round(sales_trend_median, 2)))
            existing.total_projection = total_projection
            existing.amount_to_bake = amount_to_bake
            existing.synced_to_sheets = False
            plans.append(existing)
        else:
            bp = BakePlan(
                plan_date=plan_date,
                flavor_id=flav.id,
                amount_to_bake=amount_to_bake,
                website_demand=website_demand,
                missing_for_malls=missing_for_malls,
                closing_inv_yesterday=total_closing,
                mall_forecast=Decimal(str(round(mall_forecast, 2))),
                sales_trend_median=Decimal(str(round(sales_trend_median, 2))),
                total_projection=total_projection,
            )
            db.add(bp)
            plans.append(bp)

    db.commit()
    return plans
