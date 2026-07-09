"""
FastAPI backend for VendorAI.

Run with:  uvicorn backend.main:app --reload
Docs at:   http://127.0.0.1:8000/docs
"""
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.database import init_db, get_db, get_or_create_default_vendor, ChatHistory, Vendor, Conversation
from backend.schemas import ChatRequest, ChatResponse, VendorCreate, ConversationCreate, ConversationUpdate
from backend.graph import run_chat_flow
from backend import analytics, export_utils

app = FastAPI(title="VendorAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"status": "ok", "service": "VendorAI API"}


@app.post("/vendors", response_model=dict)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)):
    vendor = Vendor(name=payload.name, phone=payload.phone, preferred_language=payload.preferred_language)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return {"id": vendor.id, "name": vendor.name}

@app.get("/vendors/{vendor_id}", response_model=dict)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        vendor = get_or_create_default_vendor(db)
    return {"id": vendor.id, "name": vendor.name, "preferred_language": vendor.preferred_language}


@app.patch("/vendors/{vendor_id}", response_model=dict)
def update_vendor(vendor_id: int, payload: dict, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if payload.get("name"):
        vendor.name = payload["name"]
    db.commit()
    db.refresh(vendor)
    return {"id": vendor.id, "name": vendor.name}


def _make_title(message: str) -> str:
    title = message.strip().split("\n")[0]
    return (title[:47] + "...") if len(title) > 50 else (title or "New chat")


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == payload.vendor_id).first()
    if not vendor:
        vendor = get_or_create_default_vendor(db)

    conversation = None
    if payload.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id, Conversation.vendor_id == vendor.id)
            .first()
        )
    if not conversation:
        conversation = Conversation(vendor_id=vendor.id, title=_make_title(payload.message))
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    final_state = run_chat_flow(db, vendor.id, payload.message, payload.language)

    log = ChatHistory(
        vendor_id=vendor.id,
        conversation_id=conversation.id,
        message=payload.message,
        response=final_state.get("response_text", ""),
        intent=final_state.get("intent", "unknown"),
        language=final_state.get("language", "en"),
    )
    db.add(log)
    conversation.updated_at = datetime.utcnow()
    db.commit()

    return ChatResponse(
        reply=final_state.get("response_text", ""),
        intent=final_state.get("intent", "unknown"),
        data=final_state.get("response_data", {}),
        language=final_state.get("language", "en"),
        conversation_id=conversation.id,
    )


@app.post("/conversations")
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    convo = Conversation(vendor_id=payload.vendor_id, title=payload.title or "New chat")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return {"id": convo.id, "title": convo.title, "pinned": bool(convo.pinned), "updated_at": convo.updated_at.isoformat()}


@app.get("/conversations/{vendor_id}")
def list_conversations(vendor_id: int, q: str = "", db: Session = Depends(get_db)):
    query = db.query(Conversation).filter(Conversation.vendor_id == vendor_id)
    if q:
        query = query.filter(Conversation.title.ilike(f"%{q}%"))
    convos = query.order_by(Conversation.pinned.desc(), Conversation.updated_at.desc()).all()
    return [
        {"id": c.id, "title": c.title, "pinned": bool(c.pinned), "updated_at": c.updated_at.isoformat()}
        for c in convos
    ]


@app.patch("/conversations/{conversation_id}")
def update_conversation(conversation_id: int, payload: ConversationUpdate, db: Session = Depends(get_db)):
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if payload.title is not None:
        convo.title = payload.title
    if payload.pinned is not None:
        convo.pinned = int(payload.pinned)
    db.commit()
    return {"id": convo.id, "title": convo.title, "pinned": bool(convo.pinned)}


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(convo)
    db.commit()
    return {"deleted": True}


@app.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.conversation_id == conversation_id)
        .order_by(ChatHistory.created_at.asc())
        .all()
    )
    return [
        {"message": r.message, "response": r.response, "intent": r.intent,
         "language": r.language, "created_at": r.created_at.isoformat()}
        for r in rows
    ]


@app.get("/dashboard/{vendor_id}")
def dashboard(vendor_id: int, period: str = "month", db: Session = Depends(get_db)):
    profit = analytics.compute_profit(db, vendor_id, period)
    report = analytics.compute_report(db, vendor_id, period)
    inventory = analytics.compute_inventory_status(db, vendor_id)
    restock = analytics.compute_restock_suggestions(db, vendor_id)
    return {"profit": profit, "report": report, "inventory": inventory, "restock": restock}


@app.get("/reports/{vendor_id}")
def reports(vendor_id: int, period: str = "month", db: Session = Depends(get_db)):
    return analytics.compute_report(db, vendor_id, period)


@app.get("/inventory/{vendor_id}")
def inventory(vendor_id: int, db: Session = Depends(get_db)):
    return analytics.compute_inventory_status(db, vendor_id)


@app.get("/history/{vendor_id}")
def chat_history(vendor_id: int, limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.vendor_id == vendor_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {"message": r.message, "response": r.response, "intent": r.intent,
         "language": r.language, "created_at": r.created_at.isoformat()}
        for r in reversed(rows)
    ]


@app.get("/export/{vendor_id}")
def export_report(vendor_id: int, format: str = "csv", period: str = "month", db: Session = Depends(get_db)):
    if format == "csv":
        content = export_utils.export_report_csv(db, vendor_id, period)
        return Response(
            content=content, media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=vendorai_report_{period}.csv"},
        )
    elif format == "pdf":
        content = export_utils.export_report_pdf(db, vendor_id, period)
        return Response(
            content=content, media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=vendorai_report_{period}.pdf"},
        )
    else:
        raise HTTPException(status_code=400, detail="format must be 'csv' or 'pdf'")
