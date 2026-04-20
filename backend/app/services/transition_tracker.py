"""
Transition tracker — monitors DB data quality to determine when each
flavor/location is ready to switch from sheet-read to DB-computed medians.

Phase 1 (current): log-only mode. The platform still uses sheet values,
but logs which flavor/location pairs would be ready to switch.

Phase 2 (future): enables actual auto-switching with drift detection.
"""

import logging
import statistics
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.daily_sales import DailySales
from app.models.flavor import Flavor
from app.models.location import Location

logger = logging.getLogger(__name__)


def count_db_data_quality(
    db: Session,
    location_id: int,
    flavor_id: int,
    target_date: date,
    weeks: int = 4,
) -> dict:
    """
    Check how many of the lookback weeks have valid 2-day-sum data in DB.
    Returns: {weeks_available, weeks_needed, ready, db_median}
    """
    weeks_with_data = 0
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
                DailySales.source == "clover",  # Only trust real Clover data
            )
            .all()
        )
        qty_map = {r.sale_date: r.quantity for r in rows}
        total = qty_map.get(day1, 0) + qty_map.get(day2, 0)

        if total > 0:
            weeks_with_data += 1
            two_day_sums.append(total)

    db_median = statistics.median(two_day_sums) if two_day_sums else 0.0

    return {
        "weeks_available": weeks_with_data,
        "weeks_needed": weeks,
        "ready": weeks_with_data >= weeks,
        "db_median": db_median,
    }


def get_transition_status(db: Session, target_date: date | None = None) -> dict:
    """
    Get readiness status for every flavor/location pair.
    Returns summary stats + per-pair details.
    """
    if target_date is None:
        target_date = date.today()

    locations = db.query(Location).filter(Location.is_active.is_(True)).order_by(Location.sort_order).all()
    flavors = db.query(Flavor).filter(Flavor.is_active.is_(True)).order_by(Flavor.sort_order).all()

    pairs = []
    ready_count = 0
    total_count = 0

    for loc in locations:
        for flav in flavors:
            if flav.code not in "ABCDEFGHIJKLMN":
                continue
            quality = count_db_data_quality(db, loc.id, flav.id, target_date)
            pairs.append({
                "location": loc.display_name,
                "flavor": f"{flav.code} {flav.name}",
                "weeks_available": quality["weeks_available"],
                "weeks_needed": quality["weeks_needed"],
                "ready": quality["ready"],
                "db_median": quality["db_median"],
            })
            total_count += 1
            if quality["ready"]:
                ready_count += 1

    return {
        "date": str(target_date),
        "summary": {
            "ready": ready_count,
            "total": total_count,
            "percent_ready": round(ready_count / total_count * 100) if total_count else 0,
        },
        "pairs": pairs,
    }


def log_transition_progress(db: Session, target_date: date) -> None:
    """
    Log how many flavor/location pairs are ready to switch.
    Called during plan generation.
    """
    status = get_transition_status(db, target_date)
    s = status["summary"]
    logger.info(
        f"Transition progress: {s['ready']}/{s['total']} "
        f"({s['percent_ready']}%) flavor/location pairs ready to switch from sheet to DB"
    )
