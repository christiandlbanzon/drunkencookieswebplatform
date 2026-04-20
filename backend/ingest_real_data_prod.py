"""
Ingest real sales data from Clover POS into the production Cloud SQL database.
Connects directly to Cloud SQL via public IP.

Usage: python ingest_real_data_prod.py [--days 35]
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timedelta, date
from pathlib import Path
from collections import defaultdict

# Set up legacy imports FIRST
DEPLOY_DIR = Path("E:/prog fold/Drunken cookies/operations automations/deploy")
sys.path.insert(0, str(DEPLOY_DIR))

# Now our app
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(str(DEPLOY_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

import pytz
import psycopg2
from psycopg2.extras import execute_values

# Legacy Clover fetchers
from src.fetch_clover_data import CloverDataFetcher
from src.fetch_all_merchants import fetch_all_merchants
from src.transform_data import DataTransformer

PR_TZ = pytz.timezone("America/Puerto_Rico")

# Location name mapping: Clover names -> DB names
LOCATION_MAP = {
    "San Patricio": 1, "Plaza del Sol": 2, "PlazaSol": 2,
    "VSJ": 3, "Viejo San Juan": 3, "Old San Juan": 3,
    "Montehiedra": 4, "Plaza": 5, "Plaza Las Americas": 5,
    "Plaza Carolina": 6,
}

# Flavor name matching
FLAVOR_PATTERNS = {
    "chocolate chip nutella": 1, "choc chip nutella": 1,
    "signature chocolate chip": 2, "sig chocolate chip": 2, "signature choc": 2,
    "cookies & cream": 3, "cookies and cream": 3,
    "white chocolate macadamia": 4, "white choc mac": 4, "macadamia": 4,
    "strawberry cheesecake": 5, "strawberry cheese": 5,
    "brookie with nutella": 8, "brookie nutella": 8,
    "brookie": 6,
    "sticky toffee pudding": 7, "sticky toffee": 7,
    "guava crumble": 9, "guava": 9,
    "churro with caramel": 10, "churro": 10,
    "vanilla coconut cream": 11, "coconut cream": 11,
    "s'mores": 12, "smore": 12, "s'more": 12,
    "birthday cake": 13, "birthday": 13,
    "cheesecake with biscoff": 14, "biscoff": 14, "cheesecake biscoff": 14,
}


def match_flavor_id(name: str) -> int | None:
    lower = name.lower().strip()
    # Exact
    if lower in FLAVOR_PATTERNS:
        return FLAVOR_PATTERNS[lower]
    # Contains
    for pattern, fid in FLAVOR_PATTERNS.items():
        if pattern in lower or lower in pattern:
            return fid
    # Word overlap
    words = set(lower.split())
    for pattern, fid in FLAVOR_PATTERNS.items():
        if len(words & set(pattern.split())) >= 2:
            return fid
    return None


def ingest_day(target_date, conn):
    """Fetch one day from Clover, transform, insert into DB."""
    logger.info(f"Fetching {target_date.strftime('%Y-%m-%d')}...")

    try:
        orders = fetch_all_merchants(target_date)
    except Exception as e:
        logger.error(f"  Failed to fetch: {e}")
        return 0

    if not orders:
        logger.info(f"  No orders")
        return 0

    transformer = DataTransformer()
    try:
        item_sales = transformer.extract_item_sales(orders, target_date)
    except Exception as e:
        logger.error(f"  Transform failed: {e}")
        return 0

    cookie_sales = item_sales.get("Cookies", [])
    if not cookie_sales:
        logger.info(f"  No cookie sales")
        return 0

    # Aggregate by (location_id, flavor_id)
    agg = defaultdict(int)
    for sale in cookie_sales:
        loc_name = sale.get("Location", "")
        loc_id = LOCATION_MAP.get(loc_name)
        if not loc_id:
            continue
        flavor_name = sale.get("Flavor Name", "")
        flavor_id = match_flavor_id(flavor_name)
        if not flavor_id:
            continue
        agg[(loc_id, flavor_id)] += int(sale.get("Quantity Sold", 0))

    if not agg:
        logger.info(f"  No matched cookies")
        return 0

    sale_date = target_date.date() if hasattr(target_date, 'date') else target_date

    # Batch upsert
    rows = [(sale_date, loc_id, flav_id, qty, 'clover', False)
            for (loc_id, flav_id), qty in agg.items()]

    cur = conn.cursor()
    execute_values(
        cur,
        """INSERT INTO daily_sales (sale_date, location_id, flavor_id, quantity, source, synced_to_sheets)
           VALUES %s
           ON CONFLICT (sale_date, location_id, flavor_id)
           DO UPDATE SET quantity = EXCLUDED.quantity, source = EXCLUDED.source""",
        rows,
    )
    conn.commit()
    cur.close()

    logger.info(f"  Upserted {len(rows)} records from {len(cookie_sales)} raw rows")
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=35)
    parser.add_argument("--db-host", default="34.31.68.95")
    parser.add_argument("--db-pass", default=None)
    args = parser.parse_args()

    # Get password from Secret Manager if not provided
    db_pass = args.db_pass
    if not db_pass:
        import subprocess
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest",
             "--secret=dc-platform-db-password", "--project=boxwood-chassis-332307"],
            capture_output=True, text=True
        )
        db_pass = result.stdout.strip()

    conn = psycopg2.connect(
        host=args.db_host, dbname="drunken_cookies",
        user="platform", password=db_pass
    )
    logger.info(f"Connected to Cloud SQL at {args.db_host}")

    # Clear mock data first
    cur = conn.cursor()
    cur.execute("DELETE FROM daily_sales WHERE source = 'mock'")
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    if deleted:
        logger.info(f"Cleared {deleted} mock records")

    now_pr = datetime.now(PR_TZ)
    total = 0

    for day_offset in range(args.days, 0, -1):
        target = (now_pr - timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        total += ingest_day(target, conn)

    conn.close()
    logger.info(f"Done! Total: {total} records ingested over {args.days} days")


if __name__ == "__main__":
    main()
