"""
Pydantic schemas.

`ExtractionResult` is the ONLY contract between the LLM and the rest of the
system. The LLM's entire job is to turn messy natural language into a valid
instance of this schema. If it can't, intent="unknown" and the backend asks
the user to rephrase -- the LLM is never trusted to touch the database.
"""
from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

Intent = Literal[
    "add_sale",
    "add_expense",
    "check_profit",
    "check_report",
    "check_inventory",
    "restock_suggestion",
    "unknown",
]


class SaleEntry(BaseModel):
    product: str
    quantity: float = 1
    unit: Optional[str] = "pcs"
    unit_price: Optional[float] = None
    total_amount: float
    date: Optional[str] = None  # ISO yyyy-mm-dd; backend defaults to today if absent

    @field_validator("product")
    @classmethod
    def clean_product(cls, v):
        return v.strip().lower()


class ExpenseEntry(BaseModel):
    item: str
    amount: float
    category: Optional[str] = "general"
    quantity: Optional[float] = None   # set if this expense is also a stock purchase
    unit: Optional[str] = None
    date: Optional[str] = None

    @field_validator("item")
    @classmethod
    def clean_item(cls, v):
        return v.strip().lower()


class QueryParams(BaseModel):
    period: Optional[Literal["today", "week", "month", "all"]] = "today"
    product: Optional[str] = None


class ExtractionResult(BaseModel):
    intent: Intent
    sales: List[SaleEntry] = Field(default_factory=list)
    expenses: List[ExpenseEntry] = Field(default_factory=list)
    query_params: QueryParams = Field(default_factory=QueryParams)
    language_detected: Optional[str] = "en"
    confidence: float = 1.0
    raw_llm_text: Optional[str] = None  # kept for debugging / LangSmith traces


# ---------- API request/response models ----------

class ChatRequest(BaseModel):
    vendor_id: int = 1
    message: str
    language: Optional[str] = None  # auto-detect if not provided
    conversation_id: Optional[int] = None  # None -> backend creates a new conversation


class ChatResponse(BaseModel):
    reply: str
    intent: str
    data: Optional[dict] = None
    language: str = "en"
    conversation_id: int


class VendorCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    preferred_language: str = "en"


class ConversationCreate(BaseModel):
    vendor_id: int = 1
    title: Optional[str] = "New chat"


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None
