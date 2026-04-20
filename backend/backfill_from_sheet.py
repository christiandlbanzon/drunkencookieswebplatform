"""
One-time backfill: read all historical sales from the Sales History Google Sheet
and import into the daily_sales table. After this runs, the platform DB will have
months of history matching what the sheet has.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

import psycopg2
from datetime import date
from google.oauth2 import service_account
from googleapiclient.discovery import build

SALES_SHEET_ID = "1OrhmZgQRbMpzewqvdQd6Wipv-sIC4s1gEw9aJO-ldgE"
SERVICE_ACCOUNT = "E:/prog fold/Drunken cookies/operations automations/deploy/service_account.json"

# Tab name -> location_id in DB
LOCATION_MAP = {
    "San Patricio": 1,
    "PlazaSol": 2,
    "VSJ": 3,
    "Montehiedra": 4,
    "Plaza": 5,
    "Plaza Carolina": 6,
}

# Flavor code -> flavor_id in DB (matches our seed)
FLAVOR_CODES = {
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7,
    "H": 8, "I": 9, "J": 10, "K": 11, "L": 12, "M": 13, "N": 14,
}


def clean_header(text: str) -> str:
    """Match the sheet's header cleaning: strip prefix, special chars, lowercase."""
    cleaned = re.sub(r"^[A-Z]\s*-\s*", "", text)
    cleaned = re.sub(r"[^a-z0-9]", "", cleaned.lower())
    return cleaned


# Flavor name -> code (cleaned versions)
FLAVOR_NAME_TO_CODE = {
    "chocolatechipnutella": "A",
    "signaturechocolatechip": "B",
    "cookiescream": "C",
    "whitechocolatemacadamia": "D",
    "strawberrycheesecake": "E",
    "brookie": "F",
    "stickytoffeepudding": "G",  # Old name
    "dubaichocolate": "G",       # New name
    "brookiewithnutella": "H",
    "guavacrumble": "I",         # Old name
    "linzercake": "I",           # New name (launch 04/17/26)
    "churrowithcaramel": "J",
    "vanillacoconutcream": "K",
    "smores": "L",
    "birthdaycake": "M",
    "cheesecakewithbiscoff": "N",
}


def main():
    db_pass = os.environ.get("DB_PASS")
    if not db_pass:
        print("ERROR: Set DB_PASS env var")
        sys.exit(1)

    # Connect to Cloud SQL via public IP
    conn = psycopg2.connect(
        host="34.31.68.95",
        dbname="drunken_cookies",
        user="platform",
        password=db_pass,
    )
    cur = conn.cursor()

    # Connect to Google Sheets
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=creds)

    grand_total = 0
    grand_skipped = 0

    for tab_name, location_id in LOCATION_MAP.items():
        print(f"\n=== {tab_name} (location_id={location_id}) ===")

        # Read all data from the tab
        result = service.spreadsheets().values().get(
            spreadsheetId=SALES_SHEET_ID,
            range=f"'{tab_name}'!A1:AZ",
        ).execute()
        rows = result.get("values", [])

        if not rows:
            print(f"  No data in {tab_name}")
            continue

        headers = rows[0]
        data_rows = rows[1:]

        # Map column index -> flavor_id
        # First occurrence wins (matches sheet's MATCH(target, headers, 0) behavior)
        col_to_flavor = {}
        seen_flavors = set()
        for col_idx, header in enumerate(headers):
            if col_idx == 0:
                continue
            cleaned = clean_header(header)
            code = FLAVOR_NAME_TO_CODE.get(cleaned)
            if code and code not in seen_flavors:
                col_to_flavor[col_idx] = FLAVOR_CODES[code]
                seen_flavors.add(code)

        print(f"  Mapped {len(col_to_flavor)} unique flavor columns")

        # Process each data row, deduplicating by (date, flavor_id)
        # Sheet may have duplicate date rows — keep the highest quantity
        records_dict = {}  # {(date, flavor_id): qty}
        skipped = 0
        for row in data_rows:
            if not row or not row[0]:
                continue
            try:
                date_str = row[0]
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                    continue
                sale_date = date.fromisoformat(date_str)
            except (ValueError, TypeError):
                skipped += 1
                continue

            for col_idx, flavor_id in col_to_flavor.items():
                if col_idx >= len(row):
                    continue
                val = row[col_idx]
                if not val:
                    continue
                try:
                    qty = int(float(val))
                    if qty > 0:
                        key = (sale_date, flavor_id)
                        # Take max if duplicate (most reliable interpretation)
                        records_dict[key] = max(records_dict.get(key, 0), qty)
                except (ValueError, TypeError):
                    continue

        records = [
            (sale_date, location_id, flavor_id, qty, "clover", False)
            for (sale_date, flavor_id), qty in records_dict.items()
        ]

        # Batch upsert
        if records:
            from psycopg2.extras import execute_values
            execute_values(
                cur,
                """
                INSERT INTO daily_sales (sale_date, location_id, flavor_id, quantity, source, synced_to_sheets)
                VALUES %s
                ON CONFLICT (sale_date, location_id, flavor_id) DO UPDATE
                SET quantity = EXCLUDED.quantity, source = EXCLUDED.source
                """,
                records,
                template="(%s, %s, %s, %s, %s, %s)",
                page_size=500,
            )
            conn.commit()

        print(f"  Inserted {len(records)} records, skipped {skipped} bad rows")
        grand_total += len(records)
        grand_skipped += skipped

    cur.close()
    conn.close()
    print(f"\n=== DONE ===")
    print(f"Total inserted: {grand_total}")
    print(f"Total skipped: {grand_skipped}")


if __name__ == "__main__":
    main()
