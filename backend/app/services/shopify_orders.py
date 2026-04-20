"""
Shopify website orders service.
Fetches today's online orders and splits them into two time windows:
- Midnight to 6PM
- 6:01PM to Midnight
Used to populate the two website order columns in the dispatch bake summary.
"""

import logging
from datetime import date, datetime, time
from collections import defaultdict

from sqlalchemy.orm import Session

from app.services.clover_ingest import _setup_legacy_imports, match_flavor_id

logger = logging.getLogger(__name__)


def fetch_website_orders(target_date: date) -> dict:
    """
    Fetch Shopify orders for a date, split into two time windows.
    Returns: {
        "midnight_6pm": {flavor_id: quantity, ...},
        "6pm_midnight": {flavor_id: quantity, ...},
    }
    """
    deploy_dir = _setup_legacy_imports()
    if not deploy_dir:
        return {"midnight_6pm": {}, "6pm_midnight": {}}

    import os
    original_cwd = os.getcwd()
    os.chdir(str(deploy_dir))

    try:
        from src.fetch_shopify_data import fetch_shopify_orders

        target_dt = datetime.combine(target_date, datetime.min.time())
        orders = fetch_shopify_orders(target_dt)

        midnight_6pm = defaultdict(int)
        after_6pm = defaultdict(int)
        cutoff_6pm = int(datetime.combine(target_date, time(18, 0)).timestamp() * 1000)

        for order in orders:
            created = order.get("createdTime", 0)
            line_items = order.get("lineItems", {}).get("elements", [])

            for item in line_items:
                item_name = item.get("name", "") or item.get("item", {}).get("name", "")
                qty = item.get("quantity", 1)
                flavor_id = match_flavor_id(item_name)
                if not flavor_id:
                    continue

                if created < cutoff_6pm:
                    midnight_6pm[flavor_id] += qty
                else:
                    after_6pm[flavor_id] += qty

        return {
            "midnight_6pm": dict(midnight_6pm),
            "6pm_midnight": dict(after_6pm),
            "total_orders": len(orders),
        }

    except Exception as e:
        logger.error(f"Shopify fetch failed: {e}", exc_info=True)
        return {"midnight_6pm": {}, "6pm_midnight": {}, "error": str(e)}

    finally:
        os.chdir(original_cwd)
