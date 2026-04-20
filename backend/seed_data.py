"""
Seed the database with initial locations, flavors, and admin user.
Run: python seed_data.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from passlib.context import CryptContext
from app.database import engine, SessionLocal, Base
from app.models import Location, Flavor, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Seed locations (from merchants.json)
    locations = [
        ("San Patricio", "San Patricio", "Y3JSKHZKVKYM1", "BXH2KACECKDA2", 1),
        ("PlazaSol", "Plaza del Sol", "J14BXNH1WDT71", "6B0N056EAXCDA", 2),
        ("VSJ", "Viejo San Juan", "QJD3EASTRDBX1", "CYF77ZMHW5MYY", 3),
        ("Montehiedra", "Montehiedra", "FNK14Z5E7CAA1", "X9Y7W6J4W6WZP", 4),
        ("Plaza", "Plaza Las Americas", "3YCBMZQ6SFT71", "AHQ1T93FPV3XP", 5),
        ("Plaza Carolina", "Plaza Carolina", "S322BTDA07H71", "43XNCHCCX6F4A", 6),
    ]
    for name, display, merchant_id, cat_id, sort in locations:
        if not db.query(Location).filter(Location.name == name).first():
            db.add(Location(
                name=name,
                display_name=display,
                clover_merchant_id=merchant_id,
                cookie_category_id=cat_id,
                sort_order=sort,
            ))

    # Seed flavors (A-N from SYSTEM_OVERVIEW.md)
    flavors = [
        ("A", "Chocolate Chip Nutella", 1),
        ("B", "Signature Chocolate Chip", 2),
        ("C", "Cookies & Cream", 3),
        ("D", "White Chocolate Macadamia", 4),
        ("E", "Strawberry Cheesecake", 5),
        ("F", "Brookie", 6),
        ("G", "Dubai Chocolate", 7),
        ("H", "Brookie with Nutella", 8),
        ("I", "Linzer Cake", 9),
        ("J", "Churro with Caramel", 10),
        ("K", "Vanilla Coconut Cream", 11),
        ("L", "S'mores", 12),
        ("M", "Birthday Cake", 13),
        ("N", "Cheesecake with Biscoff", 14),
    ]
    for code, name, sort in flavors:
        if not db.query(Flavor).filter(Flavor.code == code).first():
            db.add(Flavor(code=code, name=name, sort_order=sort, category="cookie"))

    # Seed cookie shots (from SYSTEM_OVERVIEW.md: below row ~19 in Mall PARs)
    cookie_shots = [
        ("S1", "Cookie Shot Chocolate Chips", 15),
        ("S2", "Cookie Shot Cookies & Cream", 16),
    ]
    for code, name, sort in cookie_shots:
        if not db.query(Flavor).filter(Flavor.code == code).first():
            db.add(Flavor(code=code, name=name, sort_order=sort, is_core=False, category="shot"))

    # Seed admin user
    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(
            username="admin",
            password_hash=pwd_context.hash("admin123"),
            display_name="Admin",
            role="admin",
        ))

    # Seed demo users for each role
    demo_users = [
        ("kitchen1", "kitchen123", "Kitchen Staff", "kitchen", None),
        ("dispatch1", "dispatch123", "Dispatch Team", "dispatch", None),
        ("store_sp", "store123", "Store Manager - San Patricio", "store_manager", 1),
        ("ops_mgr", "ops123", "Operations Manager", "ops_manager", None),
    ]
    for uname, pwd, dname, role, loc_id in demo_users:
        if not db.query(User).filter(User.username == uname).first():
            db.add(User(
                username=uname,
                password_hash=pwd_context.hash(pwd),
                display_name=dname,
                role=role,
                location_id=loc_id,
            ))

    db.commit()
    db.close()
    print("Seed data inserted successfully.")


if __name__ == "__main__":
    seed()
