"""
Central configuration for VendorAI.
Loads settings from environment variables (see .env.example).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- LLM provider settings ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # "openai" | "grok" | "auto" | "fallback"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-2-latest")
GROK_BASE_URL = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")

# Whisper / speech-to-text (optional, used by frontend voice input)
WHISPER_PROVIDER = os.getenv("WHISPER_PROVIDER", "openai")  # "openai" | "none"

# --- Database ---
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "vendorai.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

# --- App ---
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
LOW_STOCK_THRESHOLD_DEFAULT = float(os.getenv("LOW_STOCK_THRESHOLD_DEFAULT", "5"))

# --- LangSmith tracing (optional) ---
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "vendorai")

if LANGCHAIN_TRACING_V2.lower() == "true" and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

# --- FastAPI backend URL (used by the Streamlit frontend) ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
