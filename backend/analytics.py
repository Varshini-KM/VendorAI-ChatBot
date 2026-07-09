"""
All analytical number-crunching lives here, using pandas. Handlers call
these functions and pass the *results* (plain dicts) to the LLM for
natural-language phrasing -- the LLM never computes numbers itself.
"""
from datetime import date, timedelta
import pandas as pd
from sqlalchemy.orm import Session

from backend.database import Sale, Expense, InventoryItem


def _period_bounds(period: str) -> tuple[date, date]:
    today = date.today()
    if period == "today":
        return today, today
    if period == "week":
        return today - timedelta(days=today.weekday()), today
    if period == "month":
        return today.replace(day=1), today
    return date(2000, 1, 1), today  # "all"


def _sales_df(db: Session, vendor_id: int, start: date, end: date) -> pd.DataFrame:
    rows = (
        db.query(Sale)
        .filter(Sale.vendor_id == vendor_id, Sale.sale_date >= start, Sale.sale_date <= end)
        .all()
    )
    if not rows:
        return pd.DataFrame(columns=["product", "quantity", "unit_price", "total_amount", "sale_date"])
    return pd.DataFrame([{
        "product": r.product, "quantity": r.quantity, "unit_price": r.unit_price,
        "total_amount": r.total_amount, "sale_date": r.sale_date,
    } for r in rows])


def _expenses_df(db: Session, vendor_id: int, start: date, end: date) -> pd.DataFrame:
    rows = (
        db.query(Expense)
        .filter(Expense.vendor_id == vendor_id, Expense.expense_date >= start, Expense.expense_date <= end)
        .all()
    )
    if not rows:
        return pd.DataFrame(columns=["item", "amount", "category", "expense_date"])
    return pd.DataFrame([{
        "item": r.item, "amount": r.amount, "category": r.category, "expense_date": r.expense_date,
    } for r in rows])


def compute_profit(db: Session, vendor_id: int, period: str = "today") -> dict:
    start, end = _period_bounds(period)
    sales_df = _sales_df(db, vendor_id, start, end)
    exp_df = _expenses_df(db, vendor_id, start, end)

    total_sales = float(sales_df["total_amount"].sum()) if not sales_df.empty else 0.0
    total_expenses = float(exp_df["amount"].sum()) if not exp_df.empty else 0.0

    return {
        "period": period,
        "start_date": str(start),
        "end_date": str(end),
        "total_sales": round(total_sales, 2),
        "total_expenses": round(total_expenses, 2),
        "profit": round(total_sales - total_expenses, 2),
    }


def compute_report(db: Session, vendor_id: int, period: str = "today") -> dict:
    start, end = _period_bounds(period)
    sales_df = _sales_df(db, vendor_id, start, end)
    exp_df = _expenses_df(db, vendor_id, start, end)

    top_products = []
    if not sales_df.empty:
        grouped = (
            sales_df.groupby("product")["total_amount"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        top_products = grouped.to_dict("records")

    expense_breakdown = []
    if not exp_df.empty:
        grouped_e = (
            exp_df.groupby("category")["amount"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        expense_breakdown = grouped_e.to_dict("records")

    profit = compute_profit(db, vendor_id, period)

    return {
        "period": period,
        "start_date": str(start),
        "end_date": str(end),
        "num_sales": int(len(sales_df)),
        "num_expenses": int(len(exp_df)),
        "top_products": top_products,
        "expense_breakdown": expense_breakdown,
        **{k: v for k, v in profit.items() if k in ("total_sales", "total_expenses", "profit")},
    }


def compute_inventory_status(db: Session, vendor_id: int) -> dict:
    rows = db.query(InventoryItem).filter(InventoryItem.vendor_id == vendor_id).all()
    items = [{
        "product": r.product, "quantity": r.quantity, "unit": r.unit,
        "low_stock_threshold": r.low_stock_threshold,
    } for r in rows]
    low_stock = [i for i in items if i["quantity"] <= i["low_stock_threshold"]]
    return {"items": items, "low_stock": low_stock}


def compute_restock_suggestions(db: Session, vendor_id: int) -> dict:
    """
    Simple, explainable heuristic (great to discuss in a viva):
    - flag anything already at/below its low-stock threshold
    - flag products that sold fastest in the last 7 days relative to
      current stock ("velocity" running ahead of what's left)
    """
    inv = compute_inventory_status(db, vendor_id)
    low_stock = inv["low_stock"]

    start = date.today() - timedelta(days=7)
    sales_df = _sales_df(db, vendor_id, start, date.today())

    velocity_flags = []
    if not sales_df.empty:
        qty_sold = sales_df.groupby("product")["quantity"].sum()
        stock_map = {i["product"]: i["quantity"] for i in inv["items"]}
        for product, sold in qty_sold.items():
            daily_rate = sold / 7.0
            current_stock = stock_map.get(product, 0)
            days_left = (current_stock / daily_rate) if daily_rate > 0 else float("inf")
            if days_left < 3:
                velocity_flags.append({
                    "product": product,
                    "current_stock": current_stock,
                    "avg_daily_sales": round(daily_rate, 2),
                    "estimated_days_left": round(days_left, 1) if days_left != float("inf") else None,
                })

    return {"low_stock": low_stock, "fast_moving_low_runway": velocity_flags}


def chart_dataframes(db: Session, vendor_id: int, period: str = "month"):
    """Returns pandas DataFrames ready for Plotly charts on the dashboard."""
    start, end = _period_bounds(period)
    sales_df = _sales_df(db, vendor_id, start, end)
    exp_df = _expenses_df(db, vendor_id, start, end)

    daily_sales = pd.DataFrame(columns=["sale_date", "total_amount"])
    if not sales_df.empty:
        daily_sales = sales_df.groupby("sale_date")["total_amount"].sum().reset_index()

    daily_expenses = pd.DataFrame(columns=["expense_date", "amount"])
    if not exp_df.empty:
        daily_expenses = exp_df.groupby("expense_date")["amount"].sum().reset_index()

    product_mix = pd.DataFrame(columns=["product", "total_amount"])
    if not sales_df.empty:
        product_mix = sales_df.groupby("product")["total_amount"].sum().reset_index()

    return {
        "daily_sales": daily_sales,
        "daily_expenses": daily_expenses,
        "product_mix": product_mix,
    }
