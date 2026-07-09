"""Thin wrapper around the FastAPI backend so Streamlit pages stay simple."""
import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.config import BACKEND_URL

DEFAULT_VENDOR_ID = 1


def send_chat_message(
    message: str,
    language: str | None = None,
    vendor_id: int = DEFAULT_VENDOR_ID,
    conversation_id: int | None = None,
) -> dict:
    resp = requests.post(
        f"{BACKEND_URL}/chat",
        json={
            "vendor_id": vendor_id,
            "message": message,
            "language": language,
            "conversation_id": conversation_id,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def list_conversations(vendor_id: int = DEFAULT_VENDOR_ID, q: str = "") -> list:
    resp = requests.get(f"{BACKEND_URL}/conversations/{vendor_id}", params={"q": q}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def create_conversation(vendor_id: int = DEFAULT_VENDOR_ID, title: str = "New chat") -> dict:
    resp = requests.post(f"{BACKEND_URL}/conversations", json={"vendor_id": vendor_id, "title": title}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def update_conversation(conversation_id: int, title: str | None = None, pinned: bool | None = None) -> dict:
    payload = {}
    if title is not None:
        payload["title"] = title
    if pinned is not None:
        payload["pinned"] = pinned
    resp = requests.patch(f"{BACKEND_URL}/conversations/{conversation_id}", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def delete_conversation(conversation_id: int) -> dict:
    resp = requests.delete(f"{BACKEND_URL}/conversations/{conversation_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_conversation_messages(conversation_id: int) -> list:
    resp = requests.get(f"{BACKEND_URL}/conversations/{conversation_id}/messages", timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_dashboard(period: str = "month", vendor_id: int = DEFAULT_VENDOR_ID) -> dict:
    resp = requests.get(f"{BACKEND_URL}/dashboard/{vendor_id}", params={"period": period}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_reports(period: str = "month", vendor_id: int = DEFAULT_VENDOR_ID) -> dict:
    resp = requests.get(f"{BACKEND_URL}/reports/{vendor_id}", params={"period": period}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_inventory(vendor_id: int = DEFAULT_VENDOR_ID) -> dict:
    resp = requests.get(f"{BACKEND_URL}/inventory/{vendor_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_chat_history(vendor_id: int = DEFAULT_VENDOR_ID, limit: int = 50) -> list:
    resp = requests.get(f"{BACKEND_URL}/history/{vendor_id}", params={"limit": limit}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_export_url(fmt: str, period: str = "month", vendor_id: int = DEFAULT_VENDOR_ID) -> str:
    return f"{BACKEND_URL}/export/{vendor_id}?format={fmt}&period={period}"


def download_export(fmt: str, period: str = "month", vendor_id: int = DEFAULT_VENDOR_ID) -> bytes:
    resp = requests.get(get_export_url(fmt, period, vendor_id), timeout=30)
    resp.raise_for_status()
    return resp.content
def get_vendor(vendor_id: int = DEFAULT_VENDOR_ID) -> dict:
    resp = requests.get(f"{BACKEND_URL}/vendors/{vendor_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def update_vendor_name(name: str, vendor_id: int = DEFAULT_VENDOR_ID) -> dict:
    resp = requests.patch(f"{BACKEND_URL}/vendors/{vendor_id}", json={"name": name}, timeout=30)
    resp.raise_for_status()
    return resp.json()
