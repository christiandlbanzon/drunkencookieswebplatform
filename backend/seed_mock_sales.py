"""
Generate 30 days of realistic mock sales data so PAR calculations
produce meaningful numbers during development.

Sales patterns based on real Drunken Cookies data from SYSTEM_OVERVIEW.md:
- Weekday sales higher than weekends for some locations
- Top sellers: Chocolate Chip Nutella, Signature Chocolate Chip, Cookies & Cream
- Lower sellers: Guava Crumble, Vanilla Coconut Cream
- ~50-150 cookies per flavor per day per location, varying by popularity
"""

import sys
import os
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, SessionLocal, Base
from app.models import Location, Flavor, DailySales, Inventory

# Realistic daily sales ranges per flavor (min, max per location)
FLAVOR_POPULARITY = {
    "A": (60, 120),   # Chocolate Chip Nutella — top seller
    "B": (55, 110),   # Signature Chocolate Chip — top seller
    "C": (45, 95),    # Cookies & Cream
    "D": (30, 70),    # White Chocolate Macadamia
    "E": (35, 80),    # Strawberry Cheesecake
    "F": (40, 85),    # Brookie
    "G": (25, 60),    # Sticky Toffee Pudding
    "H": (30, 65),    # Brookie with Nutella
    "I": (20, 50),    # Guava Crumble — lower
    "J": (30, 70),    # Churro with Caramel
    "K": (15, 45),    # Vanilla Coconut Cream — lowest
    "L": (35, 75),    # S'mores
    "M": (30, 65),    # Birthday Cake
    "N": (25, 60),    # Cheesecake with Biscoff
}

# Location multipliers (some malls sell more than others)
LOCATION_MULTIPLIERS = {
    "San Patricio": 1.1,
    "PlazaSol": 0.9,
    "VSJ": 0.85,
    "Montehiedra": 0.95,
    "Plaza": 1.15,       # Plaza Las Americas — busiest
    "Plaza Carolina": 0.9,
}


def seed_mock_sales():
    db = SessionLocal()

    locations = db.query(Location).all()
    flavors = db.query(Flavor).order_by(Flavor.sort_order).all()
    flavor_map = {f.code: f for f in flavors}

    today = date.today()
    days = 35  # 5 weeks of data for solid medians

    count = 0
    for day_offset in range(days, 0, -1):
        sale_date = today - timedelta(days=day_offset)
        is_weekend = sale_date.weekday() >= 5
        weekend_factor = 0.75 if is_weekend else 1.0  # weekends slightly lower

        for loc in locations:
            loc_mult = LOCATION_MULTIPLIERS.get(loc.name, 1.0)

            for flav in flavors:
                lo, hi = FLAVOR_POPULARITY.get(flav.code, (30, 70))
                base = random.randint(lo, hi)
                qty = max(1, int(base * loc_mult * weekend_factor + random.randint(-5, 5)))

                existing = (
                    db.query(DailySales)
                    .filter(
                        DailySales.sale_date == sale_date,
                        DailySales.location_id == loc.id,
                        DailySales.flavor_id == flav.id,
                    )
                    .first()
                )
                if not existing:
                    db.add(DailySales(
                        sale_date=sale_date,
                        location_id=loc.id,
                        flavor_id=flav.id,
                        quantity=qty,
                        source="mock",
                    ))
                    count += 1

    db.commit()
    print(f"Inserted {count} mock sales records ({days} days x {len(locations)} locations x {len(flavors)} flavors)")

    # Also seed yesterday's closing inventory (random but realistic)
    yesterday = today - timedelta(days=1)
    inv_count = 0
    for loc in locations:
        for flav in flavors:
            existing = (
                db.query(Inventory)
                .filter(
                    Inventory.inventory_date == yesterday,
                    Inventory.location_id == loc.id,
                    Inventory.flavor_id == flav.id,
                )
                .first()
            )
            if not existing:
                closing = random.randint(5, 40)
                db.add(Inventory(
                    inventory_date=yesterday,
                    location_id=loc.id,
                    flavor_id=flav.id,
                    closing_inventory=closing,
                    beginning_inventory=closing + random.randint(20, 60),
                    live_sales=random.randint(30, 80),
                ))
                inv_count += 1

    db.commit()
    db.close()
    print(f"Inserted {inv_count} inventory records for {yesterday}")


if __name__ == "__main__":
    seed_mock_sales()
