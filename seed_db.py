"""Seed the demo database with a default vendor and some sample data.

Run this inside the project (venv active):
    python vendorai/seed_db.py
"""
from backend.database import init_db, SessionLocal, get_or_create_default_vendor, Sale, Expense, InventoryItem
from datetime import date


def seed():
    init_db()
    db = SessionLocal()
    vendor = get_or_create_default_vendor(db)

    # sample inventory
    items = [
        InventoryItem(vendor_id=vendor.id, product="Coconut", quantity=50, unit="pcs", low_stock_threshold=5),
        InventoryItem(vendor_id=vendor.id, product="Mango", quantity=30, unit="pcs", low_stock_threshold=10),
    ]
    for it in items:
        db.add(it)

    # sample sales
    s1 = Sale(vendor_id=vendor.id, product="Coconut", quantity=12, total_amount=900.0, sale_date=date.today())
    s2 = Sale(vendor_id=vendor.id, product="Mango", quantity=5, total_amount=250.0, sale_date=date.today())
    db.add_all([s1, s2])

    # sample expense
    e1 = Expense(vendor_id=vendor.id, item="Onions", category="stock_purchase", amount=250.0, quantity=20, unit="kg", expense_date=date.today())
    db.add(e1)

    db.commit()
    db.close()


if __name__ == "__main__":
    seed()
    print("Seeded demo data into vendorai/data database.")
