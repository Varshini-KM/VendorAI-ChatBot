"""
One handler function per intent. These are the ONLY place that writes to
the database. Each handler takes the validated ExtractionResult + a DB
session and returns (response_text, response_data).
"""
from datetime import date, datetime as _dt
from sqlalchemy.orm import Session

from backend.database import Sale, Expense, InventoryItem
from backend.schemas import ExtractionResult
from backend import analytics
from backend.llm_service import answer_with_insight


def _parse_date(d: str | None) -> date:
    if not d:
        return date.today()
    try:
        return _dt.strptime(d, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _adjust_inventory(db: Session, vendor_id: int, product: str, delta_qty: float, unit: str = "pcs"):
    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.vendor_id == vendor_id, InventoryItem.product == product)
        .first()
    )
    if not item:
        item = InventoryItem(vendor_id=vendor_id, product=product, quantity=max(delta_qty, 0), unit=unit)
        db.add(item)
    else:
        item.quantity = max(0, (item.quantity or 0) + delta_qty)
    db.commit()


def handle_add_sale(db: Session, vendor_id: int, extraction: ExtractionResult) -> tuple[str, dict]:
    created = []
    for s in extraction.sales:
        sale = Sale(
            vendor_id=vendor_id,
            product=s.product,
            quantity=s.quantity,
            unit=s.unit or "pcs",
            unit_price=s.unit_price,
            total_amount=s.total_amount,
            sale_date=_parse_date(s.date),
        )
        db.add(sale)
        _adjust_inventory(db, vendor_id, s.product, -abs(s.quantity), s.unit or "pcs")
        created.append({"product": s.product, "quantity": s.quantity, "total_amount": s.total_amount})
    db.commit()

    if len(created) == 1:
        c = created[0]
        text = f"Recorded: sold {c['quantity']} {c['product']} for Rs. {c['total_amount']}. ✅"
    else:
        lines = "; ".join(f"{c['quantity']} {c['product']} for Rs. {c['total_amount']}" for c in created)
        text = f"Recorded {len(created)} sales: {lines}. ✅"
    return text, {"created_sales": created}


def handle_add_expense(db: Session, vendor_id: int, extraction: ExtractionResult) -> tuple[str, dict]:
    created = []
    for e in extraction.expenses:
        expense = Expense(
            vendor_id=vendor_id,
            item=e.item,
            amount=e.amount,
            category=e.category or "general",
            quantity=e.quantity,
            unit=e.unit,
            expense_date=_parse_date(e.date),
        )
        db.add(expense)
        if e.category == "stock_purchase" and e.quantity:
            _adjust_inventory(db, vendor_id, e.item, abs(e.quantity), e.unit or "pcs")
        created.append({"item": e.item, "amount": e.amount, "category": e.category})
    db.commit()

    if len(created) == 1:
        c = created[0]
        text = f"Recorded expense: {c['item']} for Rs. {c['amount']}. ✅"
    else:
        lines = "; ".join(f"{c['item']} for Rs. {c['amount']}" for c in created)
        text = f"Recorded {len(created)} expenses: {lines}. ✅"
    return text, {"created_expenses": created}


def handle_check_profit(db: Session, vendor_id: int, extraction: ExtractionResult, message: str, language: str) -> tuple[str, dict]:
    data = analytics.compute_profit(db, vendor_id, extraction.query_params.period)
    text = answer_with_insight(message, data, language)
    return text, data


def handle_check_report(db: Session, vendor_id: int, extraction: ExtractionResult, message: str, language: str) -> tuple[str, dict]:
    data = analytics.compute_report(db, vendor_id, extraction.query_params.period)
    text = answer_with_insight(message, data, language)
    return text, data


def handle_check_inventory(db: Session, vendor_id: int, extraction: ExtractionResult, message: str, language: str) -> tuple[str, dict]:
    data = analytics.compute_inventory_status(db, vendor_id)
    text = answer_with_insight(message, data, language)
    return text, data


def handle_restock_suggestion(db: Session, vendor_id: int, extraction: ExtractionResult, message: str, language: str) -> tuple[str, dict]:
    data = analytics.compute_restock_suggestions(db, vendor_id)
    text = answer_with_insight(message, data, language)
    return text, data


def handle_unknown(db: Session, vendor_id: int, extraction: ExtractionResult, message: str, language: str) -> tuple[str, dict]:
    text = (
        "I didn't quite catch that. Try something like:\n"
        "• \"I sold 12 coconuts for 900 rupees\"\n"
        "• \"bought onions for 250\"\n"
        "• \"how much profit today?\"\n"
        "• \"what should I restock?\""
    )
    return text, {}
