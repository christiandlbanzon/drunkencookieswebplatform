"""
Ingest real sales data from Clover POS via the existing automation code.
Pulls the last 35 days of sales and writes to the platform database.

Usage: python ingest_real_data.py [--days 35]
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Set up paths so legacy imports work
# IMPORTANT: deploy dir must come FIRST so `config.item_standardization` resolves
# to the deploy/config/ package, not our app/config.py
DEPLOY_DIR = Path("E:/prog fold/Drunken cookies/operations automations/deploy")
sys.path.insert(0, str(DEPLOY_DIR))
sys.path.insert(0, os.path.dirname(__file__))

os.chdir(str(DEPLOY_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

import pytz
from src.fetch_clover_data import CloverDataFetcher
from src.fetch_all_merchants import fetch_all_merchants
from src.transform_data import DataTransformer

from app.database import SessionLocal, engine, Base
from app.models import Location, Flavor, DailySales

PR_TZ = pytz.timezone("America/Puerto_Rico")

# Map location names from Clover to our DB names
LOCATION_NAME_MAP = {
    "San Patricio": "San Patricio",
    "Plaza del Sol": "PlazaSol",
    "PlazaSol": "PlazaSol",
    "VSJ": "VSJ",
    "Viejo San Juan": "VSJ",
    "Old San Juan": "VSJ",
    "Montehiedra": "Montehiedra",
    "Plaza": "Plaza",
    "Plaza Las Americas": "Plaza",
    "Plaza Carolina": "Plaza Carolina",
}


def normalize_location_name(name: str) -> str:
    """Map Clover location name to our DB location name."""
    return LOCATION_NAME_MAP.get(name, name)


def ingest_day(target_date: datetime, db, locations_map, flavors_map):
    """Fetch and ingest one day of Clover sales data."""
    logger.info(f"Fetching {target_date.strftime('%Y-%m-%d')}...")

    try:
        orders = fetch_all_merchants(target_date)
    except Exception as e:
        logger.error(f"  Failed to fetch: {e}")
        return 0

    if not orders:
        logger.info(f"  No orders found")
        return 0

    # Transform orders into item sales
    transformer = DataTransformer()
    try:
        item_sales = transformer.extract_item_sales(orders, target_date)
    except Exception as e:
        logger.error(f"  Failed to transform: {e}")
        return 0

    # item_sales is Dict[str, List[Dict]] where keys are tab names
    # Each dict has: Date, Flavor Name, Location, Paid or Free, Quantity Sold
    cookie_sales = item_sales.get("Cookies", [])
    if not cookie_sales:
        logger.info(f"  No cookie sales found")
        return 0

    # Aggregate by (location_id, flavor_id) since there can be Paid + Free rows
    # and different Clover names that map to the same DB flavor
    from collections import defaultdict
    agg = defaultdict(int)  # key: (location_id, flavor_id) -> total qty

    for sale in cookie_sales:
        loc_name = normalize_location_name(sale.get("Location", ""))
        flavor_name = sale.get("Flavor Name", "")
        qty = int(sale.get("Quantity Sold", 0))

        location = locations_map.get(loc_name)
        if not location:
            continue
        flavor = match_flavor(flavor_name, flavors_map)
        if not flavor:
            logger.debug(f"  Unmatched flavor: '{flavor_name}' at {loc_name}")
            continue

        agg[(location.id, flavor.id)] += qty

    count = 0
    sale_date = target_date.date() if hasattr(target_date, 'date') else target_date

    for (loc_id, flav_id), qty in agg.items():
        existing = (
            db.query(DailySales)
            .filter(
                DailySales.sale_date == sale_date,
                DailySales.location_id == loc_id,
                DailySales.flavor_id == flav_id,
            )
            .first()
        )
        if existing:
            existing.quantity = qty
            existing.source = "clover"
        else:
            db.add(DailySales(
                sale_date=sale_date,
                location_id=loc_id,
                flavor_id=flav_id,
                quantity=qty,
                source="clover",
            ))
        count += 1

    db.commit()
    logger.info(f"  Ingested {count} records from {len(cookie_sales)} raw rows")
    return count


def match_flavor(item_name: str, flavors_map: dict):
    """Match a Clover flavor name to our DB flavor."""
    item_lower = item_name.lower().strip()

    # Exact match
    for f in flavors_map.values():
        if f.name.lower() == item_lower:
            return f

    # Contains match
    for f in flavors_map.values():
        if f.name.lower() in item_lower or item_lower in f.name.lower():
            return f

    # Partial word match (at least 2 words)
    for f in flavors_map.values():
        f_words = set(f.name.lower().split())
        i_words = set(item_lower.split())
        if len(f_words & i_words) >= 2:
            return f

    # Special cases
    special = {
        "choc chip nutella": "A",
        "chocolate chip": "B",
        "sig chocolate chip": "B",
        "signature choc": "B",
        "cookies and cream": "C",
        "cookies & cream": "C",
        "white choc mac": "D",
        "macadamia": "D",
        "strawberry cheese": "E",
        "brookie nutella": "H",
        "brookie with": "H",
        "brookie": "F",
        "sticky toffee": "G",
        "guava": "I",
        "churro": "J",
        "coconut cream": "K",
        "vanilla coconut": "K",
        "s'more": "L",
        "smore": "L",
        "birthday": "M",
        "biscoff": "N",
        "cheesecake with": "N",
    }
    for pattern, code in special.items():
        if pattern in item_lower:
            return flavors_map.get(code)

    return None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=35, help="Number of days to fetch")
    args = parser.parse_args()

    db = SessionLocal()

    # Build lookup maps
    locations = db.query(Location).all()
    locations_map = {loc.name: loc for loc in locations}
    logger.info(f"Locations: {list(locations_map.keys())}")

    flavors = db.query(Flavor).all()
    flavors_map = {f.code: f for f in flavors}
    logger.info(f"Flavors: {[f.name for f in flavors]}")

    # Clear old mock data
    mock_count = db.query(DailySales).filter(DailySales.source == "mock").count()
    if mock_count > 0:
        db.query(DailySales).filter(DailySales.source == "mock").delete()
        db.commit()
        logger.info(f"Cleared {mock_count} mock sales records")

    now_pr = datetime.now(PR_TZ)
    total = 0

    for day_offset in range(args.days, 0, -1):
        target = (now_pr - timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        total += ingest_day(target, db, locations_map, flavors_map)

    db.close()
    logger.info(f"Done! Total records ingested: {total}")


if __name__ == "__main__":
    main()
