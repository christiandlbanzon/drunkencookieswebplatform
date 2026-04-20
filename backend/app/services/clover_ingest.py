"""
Clover POS data ingestion service.
Pulls sales data from Clover API via the legacy fetchers, transforms it,
and writes to the daily_sales table.
"""

import logging
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.daily_sales import DailySales
from app.models.location import Location
from app.models.flavor import Flavor

logger = logging.getLogger(__name__)

# Flavor name matching patterns -> flavor DB id
FLAVOR_PATTERNS = {
    "chocolate chip nutella": 1, "choc chip nutella": 1,
    "signature chocolate chip": 2, "sig chocolate chip": 2, "signature choc": 2,
    "cookies & cream": 3, "cookies and cream": 3,
    "white chocolate macadamia": 4, "white choc mac": 4, "macadamia": 4,
    "strawberry cheesecake": 5, "strawberry cheese": 5,
    "brookie with nutella": 8, "brookie nutella": 8,
    "brookie": 6,
    "sticky toffee pudding": 7, "sticky toffee": 7, "dubai chocolate": 7, "dubai choc": 7, "dubai": 7,
    "linzer cake": 9, "linzer": 9, "guava crumble": 9, "guava": 9,
    "churro with caramel": 10, "churro": 10,
    "vanilla coconut cream": 11, "coconut cream": 11,
    "s'mores": 12, "smore": 12, "s'more": 12,
    "birthday cake": 13, "birthday": 13,
    "cheesecake with biscoff": 14, "biscoff": 14, "cheesecake biscoff": 14,
}

# Location name mapping: Clover name -> DB location name
LOCATION_NAME_TO_ID = {
    "San Patricio": 1, "Plaza del Sol": 2, "PlazaSol": 2,
    "VSJ": 3, "Viejo San Juan": 3, "Old San Juan": 3,
    "Montehiedra": 4, "Plaza": 5, "Plaza Las Americas": 5,
    "Plaza Carolina": 6,
}


def match_flavor_id(name: str) -> int | None:
    lower = name.lower().strip()
    # 1. Exact match
    if lower in FLAVOR_PATTERNS:
        return FLAVOR_PATTERNS[lower]
    # 2. Contains match
    for pattern, fid in FLAVOR_PATTERNS.items():
        if pattern in lower or lower in pattern:
            return fid
    # 3. Best-match fuzzy — score ALL candidates, pick highest overlap
    #    Prevents "signature chocolate chip" (2 words) stealing from
    #    "chocolate chip nutella" (3 words)
    words = set(lower.split())
    best_id, best_overlap = None, 0
    for pattern, fid in FLAVOR_PATTERNS.items():
        overlap = len(words & set(pattern.split()))
        if overlap >= 2 and overlap > best_overlap:
            best_id, best_overlap = fid, overlap
    return best_id


def _setup_legacy_imports():
    """Add legacy automation code to sys.path."""
    # Try bundled path first (Docker / Cloud Run)
    bundled = Path(__file__).parent.parent.parent / "legacy" / "deploy"
    # Then try local dev path
    local = Path("E:/prog fold/Drunken cookies/operations automations/deploy")

    for deploy_dir in [bundled, local]:
        if deploy_dir.exists() and (deploy_dir / "src").exists():
            path_str = str(deploy_dir)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
            return deploy_dir
    return None


def ingest_sales_for_date(db: Session, target_date: date) -> dict:
    """
    Fetch sales from Clover + Shopify for a given date and upsert into daily_sales.

    Returns summary dict with counts.
    """
    deploy_dir = _setup_legacy_imports()
    if not deploy_dir:
        logger.error("Legacy automation code not found")
        return {"error": "Legacy code not available", "records": 0}

    import os
    original_cwd = os.getcwd()
    os.chdir(str(deploy_dir))

    try:
        from src.fetch_all_merchants import fetch_all_merchants
        from src.transform_data import DataTransformer

        # Fetch from Clover + Shopify
        target_dt = datetime.combine(target_date, datetime.min.time())
        orders = fetch_all_merchants(target_dt)

        if not orders:
            return {"date": str(target_date), "orders": 0, "records": 0}

        # Transform
        transformer = DataTransformer()
        item_sales = transformer.extract_item_sales(orders, target_dt)
        cookie_sales = item_sales.get("Cookies", [])

        if not cookie_sales:
            return {"date": str(target_date), "orders": len(orders), "records": 0}

        # Aggregate by (location_id, flavor_id)
        agg = defaultdict(int)
        for sale in cookie_sales:
            loc_name = sale.get("Location", "")
            loc_id = LOCATION_NAME_TO_ID.get(loc_name)
            if not loc_id:
                continue
            flavor_name = sale.get("Flavor Name", "")
            flavor_id = match_flavor_id(flavor_name)
            if not flavor_id:
                continue
            agg[(loc_id, flavor_id)] += int(sale.get("Quantity Sold", 0))

        # Batch upsert
        if agg:
            stmt = pg_insert(DailySales).values([
                {
                    "sale_date": target_date,
                    "location_id": loc_id,
                    "flavor_id": flav_id,
                    "quantity": qty,
                    "source": "clover",
                    "synced_to_sheets": False,
                }
                for (loc_id, flav_id), qty in agg.items()
            ])
            stmt = stmt.on_conflict_do_update(
                constraint="uq_daily_sales",
                set_={"quantity": stmt.excluded.quantity, "source": stmt.excluded.source},
            )
            db.execute(stmt)
            db.commit()

        # Missing-cookie alert: log flavors with 0 sales
        EXPECTED_FLAVORS = {
            1: "Chocolate Chip Nutella", 2: "Signature Chocolate Chip",
            3: "Cookies & Cream", 4: "White Chocolate Macadamia",
            5: "Strawberry Cheesecake", 6: "Brookie",
            7: "Sticky Toffee Pudding", 8: "Brookie with Nutella",
            9: "Guava Crumble", 10: "Churro with Caramel",
            11: "Vanilla Coconut Cream", 12: "S'mores",
            13: "Birthday Cake", 14: "Cheesecake with Biscoff",
        }
        found_flavors = {flav_id for (_, flav_id) in agg.keys()}
        missing = set(EXPECTED_FLAVORS.keys()) - found_flavors
        missing_names = []
        if missing:
            for fid in sorted(missing):
                missing_names.append(f"{EXPECTED_FLAVORS[fid]}")
            logger.warning(f"Missing cookie data for {target_date}: {', '.join(missing_names)} — check Clover mapping")

        logger.info(f"Ingested {len(agg)} records for {target_date} from {len(orders)} orders")
        return {
            "date": str(target_date),
            "orders": len(orders),
            "raw_cookie_rows": len(cookie_sales),
            "records": len(agg),
            "missing_flavors": missing_names,
        }

    except Exception as e:
        logger.error(f"Ingest failed for {target_date}: {e}", exc_info=True)
        return {"date": str(target_date), "error": str(e), "records": 0}

    finally:
        os.chdir(original_cwd)
