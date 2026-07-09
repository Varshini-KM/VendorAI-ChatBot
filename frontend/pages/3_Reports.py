import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from frontend.theme import inject_theme, hero
from frontend.utils.api_client import get_reports, download_export, get_chat_history

st.set_page_config(page_title="VendorAI - Reports", page_icon="📄", layout="wide")
inject_theme()
hero("📄 Reports", "Daily, weekly, and monthly breakdowns you can export and share.")

period = st.selectbox("Period", ["today", "week", "month", "all"], index=2)

try:
    report = get_reports(period)
except Exception as e:
    st.error(f"⚠️ Couldn't reach the backend. Is it running? (`uvicorn backend.main:app --reload`)\n\n{e}")
    st.stop()

st.markdown(f'<p class="va-muted">Period: {report["start_date"]} to {report["end_date"]}</p>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
for col, label, value in [
    (col1, "Total Sales", f"Rs. {report.get('total_sales', 0):.2f}"),
    (col2, "Total Expenses", f"Rs. {report.get('total_expenses', 0):.2f}"),
    (col3, "Profit", f"Rs. {report.get('profit', 0):.2f}"),
    (col4, "# Transactions", report["num_sales"] + report["num_expenses"]),
]:
    col.markdown(
        f"""<div class="va-card"><div class="va-muted">{label}</div>
        <div style="font-size:1.4rem;font-weight:700;margin-top:4px;">{value}</div></div>""",
        unsafe_allow_html=True,
    )

st.markdown("<br/>", unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.subheader("Sales by Product")
    if report["top_products"]:
        st.dataframe(pd.DataFrame(report["top_products"]), use_container_width=True, hide_index=True)
    else:
        st.info("No sales in this period.")

with c2:
    st.subheader("Expenses by Category")
    if report["expense_breakdown"]:
        st.dataframe(pd.DataFrame(report["expense_breakdown"]), use_container_width=True, hide_index=True)
    else:
        st.info("No expenses in this period.")

st.markdown("<br/>", unsafe_allow_html=True)
st.subheader("⬇️ Export")
ec1, ec2 = st.columns(2)
with ec1:
    try:
        csv_bytes = download_export("csv", period)
        st.download_button("Download CSV", data=csv_bytes, file_name=f"vendorai_report_{period}.csv", mime="text/csv", use_container_width=True)
    except Exception as e:
        st.caption(f"CSV export unavailable: {e}")
with ec2:
    try:
        pdf_bytes = download_export("pdf", period)
        st.download_button("Download PDF", data=pdf_bytes, file_name=f"vendorai_report_{period}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as e:
        st.caption(f"PDF export unavailable: {e}")

st.markdown("<br/>", unsafe_allow_html=True)
st.subheader("🕘 Recent Chat History")
try:
    history = get_chat_history(limit=30)
    if history:
        for h in history:
            st.markdown(
                f"""<div class="va-card">
                    <div><strong>You</strong> <span class="va-muted">({h['language']})</span>: {h['message']}</div>
                    <div style="margin-top:6px;"><strong>VendorAI</strong> <span class="va-badge">{h['intent']}</span>: {h['response']}</div>
                    <div class="va-muted" style="margin-top:6px;font-size:0.78rem;">{h['created_at']}</div>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.info("No chat history yet — go say hi on the Chat page!")
except Exception as e:
    st.caption(f"Couldn't load history: {e}")
