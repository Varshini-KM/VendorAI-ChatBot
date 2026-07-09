import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from frontend.theme import inject_theme, hero, card_open, card_close
from backend import config

st.set_page_config(page_title="VendorAI", page_icon="🛒", layout="wide")
inject_theme()

# ---------------- Brand banner ----------------
hero(
    "VendorAI — your everyday shop assistant",
    "Log sales and expenses, track profit, and know what to restock — just by chatting in English, Hindi, or Tamil.",
)

st.markdown(
    """
    Talk to VendorAI the way you'd talk to a shop assistant. It logs your sales
    and expenses, tracks profit, and tells you what to restock, all from
    plain sentences typed into the chat — no forms, no spreadsheets.
    """
)

st.markdown("&nbsp;", unsafe_allow_html=True)

# ---------------- Feature cards ----------------
features = [
    ("Chat", "teal", "Record sales, expenses, or ask business questions in natural language."),
    ("Dashboard", "", "A visual overview of profit, sales, and expenses at a glance."),
    ("Reports", "chili", "Daily, weekly, and monthly reports, exportable as CSV or PDF."),
    ("Inventory", "teal", "Current stock levels with automatic low-stock alerts."),
]

cols = st.columns(4)
for col, (title, variant, desc) in zip(cols, features):
    with col:
        card_open(variant)
        st.markdown(f"### {title}")
        st.markdown(f'<p class="va-muted">{desc}</p>', unsafe_allow_html=True)
        card_close()

st.markdown("---")

# ---------------- Try saying things like ----------------
st.markdown("### Try saying things like")
examples = [
    "I sold 12 coconuts for 900 rupees",
    "bought onions for 250 and tomatoes for 400",
    "how much profit did I make today?",
    "what should I restock?",
    "aaj kitna profit hua (Hindi)",
    "இந்த வாரம் என் expense எவ்வளவு (Tamil)",
]
ex_cols = st.columns(3)
for i, text in enumerate(examples):
    with ex_cols[i % 3]:
        st.markdown(
            f'<div class="va-card" style="padding:14px 16px;"><i>"{text}"</i></div>',
            unsafe_allow_html=True,
        )

st.markdown("&nbsp;", unsafe_allow_html=True)
st.page_link("pages/1_Chat.py", label="Start chatting →", icon="💬")

if not (config.OPENAI_API_KEY or config.GROK_API_KEY):
    st.info(
        "💡 Tip: No LLM API key configured yet? VendorAI still works out of the box "
        "using a built-in rule-based extractor for English messages — add your "
        "OpenAI or Grok key in `.env` any time for full multilingual accuracy.",
        icon="💡",
    )