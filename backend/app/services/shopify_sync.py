"""
Shopify order sync service.
Pulls orders from Shopify API and upserts into shopify_orders table.
"""

import json
import logging
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from decimal import Decimal

import requests
from sqlalchemy.orm import Session

from app.models.shopify_order import ShopifyOrder

logger = logging.getLogger(__name__)

# Special request detection keywords
SPECIAL_KEYWORDS = [
    "event", "catering", "party", "wedding", "celebration",
    "corporate", "office", "meeting", "conference", "gathering",
    "special request", "custom order", "bulk order",
]

SPECIAL_TYPES = {
    "wedding": "Wedding",
    "corporate": "Corporate Event",
    "office": "Corporate Event",
    "party": "Party",
    "catering": "Catering",
    "celebration": "Celebration",
    "conference": "Corporate Event",
}


def _load_shopify_config() -> dict | None:
    """Load Shopify credentials from bundled config."""
    for path in [
        Path(__file__).parent.parent.parent / "legacy" / "deploy" / "config" / "shopify_config.json",
        Path("E:/prog fold/Drunken cookies/operations automations/deploy/config/shopify_config.json"),
    ]:
        if path.exists():
            return json.loads(path.read_text())
    return None


def _detect_special_request(order: dict) -> tuple[bool, str]:
    """Check if order is a special/catering request."""
    searchable = " ".join([
        order.get("note", "") or "",
        " ".join(order.get("tags", "").split(",")) if order.get("tags") else "",
        " ".join(li.get("title", "") for li in order.get("line_items", [])),
    ]).lower()

    for keyword in SPECIAL_KEYWORDS:
        if keyword in searchable:
            for pattern, stype in SPECIAL_TYPES.items():
                if pattern in searchable:
                    return True, stype
            return True, "Special Request"
    return False, ""


def _get_delivery_status(order: dict) -> str:
    """Extract delivery status from Shopify fulfillments."""
    fulfillments = order.get("fulfillments", [])
    if not fulfillments:
        fs = order.get("fulfillment_status")
        if fs == "fulfilled":
            return "Delivered"
        if fs == "partial":
            return "Partial"
        if fs == "restocked":
            return "Restocked"
        return "Pending"

    latest = fulfillments[-1]
    shipment = (latest.get("shipment_status") or "").lower()
    status = (latest.get("status") or "").lower()

    if shipment == "delivered" or status == "success":
        return "Delivered"
    if shipment == "out_for_delivery":
        return "Out for Delivery"
    if shipment in ("in_transit", "confirmed"):
        return "In Transit"
    if shipment in ("failure", "delivery_failure") or status in ("failure", "error"):
        return "Delivery Failed"
    if status == "cancelled":
        return "Cancelled"
    return "In Transit"


def _get_tracking(order: dict) -> str:
    """Extract tracking numbers from fulfillments."""
    numbers = []
    for f in order.get("fulfillments", []):
        tn = f.get("tracking_number")
        if tn:
            numbers.append(tn)
    return ", ".join(numbers)


def _get_items_summary(order: dict) -> str:
    """Build human-readable items summary."""
    items = []
    for li in order.get("line_items", []):
        qty = li.get("quantity", 1)
        title = li.get("title", "Unknown")
        variant = li.get("variant_title", "")
        name = f"{title} - {variant}" if variant else title
        items.append(f"{qty}x {name}")
    return ", ".join(items[:10])  # Cap at 10 items


def _get_refund_info(order: dict) -> tuple[str, Decimal, date | None, str]:
    """Extract refund data."""
    refunds = order.get("refunds", [])
    if not refunds:
        return "No", Decimal(0), None, ""

    total_amount = Decimal(0)
    latest_date = None
    reason = ""

    for refund in refunds:
        for txn in refund.get("transactions", []):
            if txn.get("kind") == "refund":
                total_amount += abs(Decimal(str(txn.get("amount", 0))))
        rd = refund.get("created_at")
        if rd:
            try:
                from dateutil import parser
                parsed = parser.parse(rd).date()
                if latest_date is None or parsed > latest_date:
                    latest_date = parsed
            except Exception:
                pass
        if refund.get("note"):
            reason = refund["note"]

    if total_amount > 0:
        return "Yes", total_amount, latest_date, reason
    return "No", Decimal(0), None, ""


def sync_shopify_orders(db: Session, days: int = 7) -> dict:
    """
    Fetch recent Shopify orders and upsert into the database.
    Preserves manual fields (package_notes, feedback, endorsement).
    """
    config = _load_shopify_config()
    if not config:
        return {"error": "Shopify config not found", "synced": 0}

    store = config["STORE_NAME"]
    token = config["API_TOKEN"]
    version = config.get("API_VERSION", "2023-01")

    start_date = (date.today() - timedelta(days=days)).isoformat() + "T00:00:00Z"
    url = f"https://{store}.myshopify.com/admin/api/{version}/orders.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}

    all_orders = []
    params = {
        "created_at_min": start_date,
        "status": "any",
        "limit": 250,
    }

    try:
        while True:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            orders = resp.json().get("orders", [])
            all_orders.extend(orders)

            # Pagination
            link = resp.headers.get("Link", "")
            if 'rel="next"' in link:
                match = re.search(r'page_info=([^&>]+)', link)
                if match:
                    params = {"page_info": match.group(1), "limit": 250}
                    continue
            break

    except Exception as e:
        logger.error(f"Shopify API error: {e}")
        return {"error": str(e), "synced": 0}

    synced = 0
    for order in all_orders:
        order_number = order.get("name", f"#{order.get('id', '')}")

        try:
            from dateutil import parser as dp
            order_date = dp.parse(order.get("created_at", "")).date()
        except Exception:
            order_date = date.today()

        # Customer info
        ship = order.get("shipping_address") or {}
        cust = order.get("customer") or {}
        customer_name = f"{ship.get('first_name', cust.get('first_name', ''))} {ship.get('last_name', cust.get('last_name', ''))}".strip()
        phone = ship.get("phone") or cust.get("phone") or ""
        email = order.get("email") or cust.get("email") or ""

        # Address
        addr_parts = [ship.get("name", ""), ship.get("address1", ""), ship.get("address2", ""),
                      ship.get("city", ""), ship.get("province", ""), ship.get("zip", ""), ship.get("country", "")]
        address = ", ".join(p for p in addr_parts if p)

        is_special, special_type = _detect_special_request(order)
        delivery_status = _get_delivery_status(order)
        tracking = _get_tracking(order)
        items = _get_items_summary(order)
        refund_status, refund_amount, refund_date, refund_reason = _get_refund_info(order)
        total_price = Decimal(str(order.get("total_price", 0)))

        # Upsert — preserve manual fields
        existing = db.query(ShopifyOrder).filter(ShopifyOrder.order_number == order_number).first()
        if existing:
            existing.order_date = order_date
            existing.customer_name = customer_name
            existing.contact_phone = phone
            existing.email = email
            existing.shipping_address = address
            existing.gift_message = order.get("note", "") or ""
            existing.items_summary = items
            existing.tracking_number = tracking
            existing.delivery_status = delivery_status
            existing.is_special_request = is_special
            existing.special_request_type = special_type
            existing.refund_status = refund_status
            existing.refund_amount = refund_amount
            existing.refund_date = refund_date
            existing.refund_reason = refund_reason
            existing.total_price = total_price
            existing.financial_status = order.get("financial_status", "paid")
            # DO NOT overwrite: package_notes, feedback, endorsement
        else:
            db.add(ShopifyOrder(
                order_number=order_number,
                order_date=order_date,
                customer_name=customer_name,
                contact_phone=phone,
                email=email,
                shipping_address=address,
                gift_message=order.get("note", "") or "",
                items_summary=items,
                tracking_number=tracking,
                delivery_status=delivery_status,
                is_special_request=is_special,
                special_request_type=special_type,
                refund_status=refund_status,
                refund_amount=refund_amount,
                refund_date=refund_date,
                refund_reason=refund_reason,
                total_price=total_price,
                financial_status=order.get("financial_status", "paid"),
            ))
        synced += 1

    db.commit()
    logger.info(f"Synced {synced} Shopify orders ({days} days)")
    return {"synced": synced, "total_fetched": len(all_orders), "days": days}
