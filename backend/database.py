"""
Database layer for VendorAI.

Design principle (important for the architecture write-up):
The LLM NEVER touches this file or the DB directly. It only ever produces
structured JSON (see schemas.py). Every read/write below is plain,
auditable Python + SQL, called from backend/handlers.py.
"""
from datetime import datetime, date
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os

from backend.config import DATABASE_URL, DB_PATH

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, default="Vendor")
    phone = Column(String, nullable=True)
    preferred_language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

    sales = relationship("Sale", back_populates="vendor", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="vendor", cascade="all, delete-orphan")
    inventory = relationship("InventoryItem", back_populates="vendor", cascade="all, delete-orphan")
    chats = relationship("ChatHistory", back_populates="vendor", cascade="all, delete-orphan")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    product = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, default="pcs")
    unit_price = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=False)
    sale_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="sales")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    item = Column(String, nullable=False)
    category = Column(String, default="general")  # e.g. stock_purchase, rent, transport
    amount = Column(Float, nullable=False)
    quantity = Column(Float, nullable=True)   # optional: if this expense also restocks inventory
    unit = Column(String, nullable=True)
    expense_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="expenses")


class InventoryItem(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    product = Column(String, nullable=False)
    quantity = Column(Float, default=0)
    unit = Column(String, default="pcs")
    low_stock_threshold = Column(Float, default=5)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="inventory")


class Conversation(Base):
    """A named chat thread. Lets the sidebar show multiple conversations
    per vendor (rename/pin/delete/search), instead of one flat log."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    title = Column(String, nullable=False, default="New chat")
    pinned = Column(Integer, default=0)  # 0/1 - sqlite has no native bool
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vendor = relationship("Vendor")
    messages = relationship("ChatHistory", back_populates="conversation", cascade="all, delete-orphan")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    message = Column(String, nullable=False)
    response = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="chats")
    conversation = relationship("Conversation", back_populates="messages")


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_add_conversation_id()


def _migrate_add_conversation_id():
    """Lightweight, dependency-free migration for existing SQLite DBs created
    before conversations existed. No-op on fresh databases (column already
    exists via create_all) and no-op on non-sqlite backends."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.connect() as conn:
        cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(chat_history)")]
        if "conversation_id" not in cols:
            conn.exec_driver_sql("ALTER TABLE chat_history ADD COLUMN conversation_id INTEGER")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_default_vendor(db) -> Vendor:
    """Convenience helper: single-vendor demo mode uses vendor id=1."""
    vendor = db.query(Vendor).filter(Vendor.id == 1).first()
    if not vendor:
        vendor = Vendor(id=1, name="User", preferred_language="en")
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
    return vendor