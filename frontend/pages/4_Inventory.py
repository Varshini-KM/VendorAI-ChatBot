import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from frontend.theme import inject_theme, hero
from frontend.utils.api_client import get_inventory

st.set_page_config(page_title="VendorAI - Inventory", page_icon="📦", layout="wide")
inject_theme()
hero("📦 Inventory", "Stock levels update automatically as you record sales and purchases in chat.")

try:
    inv = get_inventory()
except Exception as e:
    st.error(f"⚠️ Couldn't reach the backend. Is it running? (`uvicorn backend.main:app --reload`)\n\n{e}")
    st.stop()

if not inv["items"]:
    st.info(
        "No inventory yet. Inventory updates automatically as you record sales "
        "(stock goes down) or stock-purchase expenses like "
        "*'bought 20kg onions for 400 to sell'* (stock goes up)."
    )
else:
    df = pd.DataFrame(inv["items"])
    df["status"] = df.apply(
        lambda r: "🔴 Low stock" if r["quantity"] <= r["low_stock_threshold"] else "🟢 OK", axis=1
    )
    st.markdown('<div class="va-card">', unsafe_allow_html=True)
    st.dataframe(
        df[["product", "quantity", "unit", "low_stock_threshold", "status"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "product": "Product",
            "quantity": "Current Qty",
            "unit": "Unit",
            "low_stock_threshold": "Low-stock threshold",
            "status": "Status",
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if inv["low_stock"]:
        st.markdown(
            f'<div class="va-card"><span class="va-badge">⚠️ {len(inv["low_stock"])} item(s) need restocking soon</span></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br/>", unsafe_allow_html=True)
st.caption(
    "💡 Tip: ask the chatbot *'what should I restock?'* for smarter, sales-velocity-based "
    "suggestions (not just a fixed low-stock threshold)."
)
