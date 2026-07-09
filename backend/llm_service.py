"""
LLM service layer.

Supports three modes, chosen automatically (LLM_PROVIDER=auto):
  1. OpenAI  (if OPENAI_API_KEY is set)
  2. Grok    (if GROK_API_KEY is set, OpenAI-compatible endpoint)
  3. Fallback rule-based extractor (no key needed at all) -- this lets the
     whole app run and be demoed end-to-end before you've wired up API keys.

Whichever mode runs, the OUTPUT CONTRACT is always an ExtractionResult.
Everything downstream (handlers.py, graph.py) is completely unaware of
which mode produced it.
"""
import json
import re
from datetime import date

from backend import config
from backend.schemas import ExtractionResult
from backend.prompts import EXTRACTION_SYSTEM_PROMPT, QA_SYSTEM_PROMPT


# --------------------------------------------------------------------------
# Provider selection
# --------------------------------------------------------------------------

def _active_provider() -> str:
    if config.LLM_PROVIDER in ("openai", "grok", "fallback"):
        return config.LLM_PROVIDER
    # auto
    if config.OPENAI_API_KEY:
        return "openai"
    if config.GROK_API_KEY:
        return "grok"
    return "fallback"


def _get_client(provider: str):
    from openai import OpenAI  # both OpenAI and Grok speak the OpenAI SDK protocol
    if provider == "openai":
        return OpenAI(api_key=config.OPENAI_API_KEY), config.OPENAI_MODEL
    if provider == "grok":
        return OpenAI(api_key=config.GROK_API_KEY, base_url=config.GROK_BASE_URL), config.GROK_MODEL
    raise ValueError("No LLM client for fallback provider")


# --------------------------------------------------------------------------
# Extraction (natural language -> structured JSON)
# --------------------------------------------------------------------------

def extract_intent(message: str, language_hint: str | None = None) -> ExtractionResult:
    provider = _active_provider()

    if provider == "fallback":
        return _fallback_extract(message)

    try:
        client, model = _get_client(provider)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content
        data = json.loads(raw)
        data["raw_llm_text"] = raw
        return ExtractionResult(**data)
    except Exception as e:
        # Never let an LLM/network hiccup crash the pipeline -- degrade gracefully.
        result = _fallback_extract(message)
        result.raw_llm_text = f"[LLM error, used fallback: {e}]"
        return result


# --------------------------------------------------------------------------
# Analytical Q&A (precomputed numbers -> friendly natural language)
# --------------------------------------------------------------------------

def answer_with_insight(user_message: str, computed_data: dict, language: str = "en") -> str:
    provider = _active_provider()

    if provider == "fallback":
        return _fallback_answer(computed_data, language)

    try:
        client, model = _get_client(provider)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Vendor asked (language={language}): {user_message}\n\n"
                        f"Precomputed data:\n{json.dumps(computed_data, default=str)}"
                    ),
                },
            ],
            temperature=0.4,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return _fallback_answer(computed_data, language)


# --------------------------------------------------------------------------
# Rule-based fallback (no API key required)
# --------------------------------------------------------------------------

_HINDI_RANGE = re.compile(r"[\u0900-\u097F]")
_TAMIL_RANGE = re.compile(r"[\u0B80-\u0BFF]")

_SALE_VERBS = ["sold", "sell", "becha", "vitten", "vittu"]
_EXPENSE_VERBS = ["bought", "purchase", "khareeda", "vaangi", "spent"]

_NUM_FOR_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*([a-zA-Z\u0900-\u097F\u0B80-\u0BFF]+)\D{0,10}?for\D{0,5}?(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SIMPLE_QTY_ITEM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)")


def _detect_language(text: str) -> str:
    if _HINDI_RANGE.search(text):
        return "hi"
    if _TAMIL_RANGE.search(text):
        return "ta"
    return "en"


def _detect_period(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["week", "hafte", "vaaram"]):
        return "week"
    if any(w in t for w in ["month", "mahine", "maasam"]):
        return "month"
    return "today"


def _fallback_extract(message: str) -> ExtractionResult:
    """
    A transparent, explainable regex-based extractor used when no LLM API
    key is configured yet. Handles the common English patterns well;
    Hindi/Tamil support here is intentionally minimal (language is still
    detected correctly) -- full multilingual accuracy is the job of the
    real LLM once a key is added.
    """
    text = message.strip()
    lower = text.lower()
    lang = _detect_language(text)

    matches = list(_NUM_FOR_RE.finditer(lower))

    is_sale = any(v in lower for v in _SALE_VERBS)
    is_expense = any(v in lower for v in _EXPENSE_VERBS)

    if matches and (is_sale or is_expense):
        # split message on "and" to catch multi-entry messages robustly
        if is_sale:
            sales = []
            for m in matches:
                qty, product, amount = float(m.group(1)), m.group(2), float(m.group(3))
                sales.append({
                    "product": product,
                    "quantity": qty,
                    "unit": "pcs",
                    "unit_price": round(amount / qty, 2) if qty else None,
                    "total_amount": amount,
                    "date": None,
                })
            return ExtractionResult(
                intent="add_sale", sales=sales, expenses=[],
                query_params={"period": "today", "product": None},
                language_detected=lang, confidence=0.6,
                raw_llm_text="[fallback rule-based extractor]",
            )
        else:
            expenses = []
            for m in matches:
                qty, item, amount = float(m.group(1)), m.group(2), float(m.group(3))
                expenses.append({
                    "item": item, "amount": amount, "category": "stock_purchase",
                    "quantity": qty, "unit": None, "date": None,
                })
            return ExtractionResult(
                intent="add_expense", sales=[], expenses=expenses,
                query_params={"period": "today", "product": None},
                language_detected=lang, confidence=0.6,
                raw_llm_text="[fallback rule-based extractor]",
            )

    # Handle "bought X for Y" without a leading quantity, and multi-clause "and"
    if is_expense and "for" in lower:
        expenses = []
        for clause in re.split(r"\band\b", lower):
            m = re.search(r"([a-zA-Z]+)\s+for\D{0,5}?(\d+(?:\.\d+)?)", clause)
            if m:
                expenses.append({
                    "item": m.group(1).strip(), "amount": float(m.group(2)),
                    "category": "stock_purchase", "quantity": None, "unit": None, "date": None,
                })
        if expenses:
            return ExtractionResult(
                intent="add_expense", sales=[], expenses=expenses,
                query_params={"period": "today", "product": None},
                language_detected=lang, confidence=0.55,
                raw_llm_text="[fallback rule-based extractor]",
            )

    if is_sale and "for" in lower:
        sales = []
        for clause in re.split(r"\band\b", lower):
            m = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)\D{0,10}for\D{0,5}?(\d+(?:\.\d+)?)", clause)
            if m:
                qty, product, amount = float(m.group(1)), m.group(2).strip(), float(m.group(3))
                sales.append({
                    "product": product, "quantity": qty, "unit": "pcs",
                    "unit_price": round(amount / qty, 2) if qty else None,
                    "total_amount": amount, "date": None,
                })
        if sales:
            return ExtractionResult(
                intent="add_sale", sales=sales, expenses=[],
                query_params={"period": "today", "product": None},
                language_detected=lang, confidence=0.55,
                raw_llm_text="[fallback rule-based extractor]",
            )

    # Question-style intents
    period = _detect_period(lower)
    if any(w in lower for w in ["profit", "kitna", "lābam", "labam"]):
        intent = "check_profit"
    elif any(w in lower for w in ["report", "sales report", "how much did i sell", "expenses"]):
        intent = "check_report"
    elif any(w in lower for w in ["stock", "inventory", "how many", "left", "irukku"]):
        intent = "check_inventory"
    elif any(w in lower for w in ["restock", "reorder", "should i buy", "order more"]):
        intent = "restock_suggestion"
    else:
        intent = "unknown"

    return ExtractionResult(
        intent=intent, sales=[], expenses=[],
        query_params={"period": period, "product": None},
        language_detected=lang, confidence=0.5 if intent != "unknown" else 0.3,
        raw_llm_text="[fallback rule-based extractor]",
    )


def _fallback_answer(data: dict, language: str) -> str:
    """Simple templated answers used when no LLM key is configured."""
    if "profit" in data:
        return (
            f"Your profit for the selected period is Rs. {data.get('profit', 0):.2f} "
            f"(sales: Rs. {data.get('total_sales', 0):.2f}, expenses: Rs. {data.get('total_expenses', 0):.2f})."
        )
    if "low_stock" in data:
        items = data.get("low_stock", [])
        if items:
            names = ", ".join(i["product"] for i in items)
            return f"You're running low on: {names}. Consider restocking soon."
        return "All your inventory levels look healthy right now."
    if "top_products" in data:
        top = data.get("top_products", [])
        if top:
            return f"Your best-selling product recently is {top[0]['product']} ({top[0]['total_amount']:.2f} in sales)."
        return "No sales recorded yet for this period."
    return "Here's what I found: " + json.dumps(data, default=str)