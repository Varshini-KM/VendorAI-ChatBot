import streamlit as st
import sys
import os
import plotly.express as px
import plotly.graph_objects as go

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from frontend.theme import inject_theme, hero
from frontend.utils.api_client import get_dashboard

st.set_page_config(page_title="VendorAI - Dashboard", page_icon="📊", layout="wide")
inject_theme()
hero("📊 Business Dashboard", "A live snapshot of sales, profit, and stock — updated every time you chat.")

period = st.selectbox("Period", ["today", "week", "month", "all"], index=2)

placeholder = st.empty()
with placeholder.container():
    sk1, sk2, sk3 = st.columns(3)
    for c in (sk1, sk2, sk3):
        c.markdown('<div class="va-card"><div class="va-muted">Loading…</div></div>', unsafe_allow_html=True)

try:
    data = get_dashboard(period)
    placeholder.empty()
except Exception as e:
    placeholder.empty()
    st.error(f"⚠️ Couldn't reach the backend. Is it running? (`uvicorn backend.main:app --reload`)\n\n{e}")
    st.stop()

profit = data["profit"]
report = data["report"]
inventory = data["inventory"]
restock = data["restock"]


def metric_card(col, label, value, accent="var(--va-accent)"):
    col.markdown(
        f"""<div class="va-card">
            <div class="va-muted">{label}</div>
            <div style="font-size:1.7rem;font-weight:700;color:{accent};margin-top:4px;">{value}</div>
        </div>""",
        unsafe_allow_html=True,
    )


col1, col2, col3 = st.columns(3)
metric_card(col1, "Total Sales", f"Rs. {profit['total_sales']:.2f}")
metric_card(col2, "Total Expenses", f"Rs. {profit['total_expenses']:.2f}", accent="var(--va-danger)")
metric_card(
    col3, "Net Profit", f"Rs. {profit['profit']:.2f}",
    accent="var(--va-success)" if profit["profit"] >= 0 else "var(--va-danger)",
)

st.markdown("<br/>", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    st.subheader("🏆 Top Products by Revenue")
    if report["top_products"]:
        fig = px.bar(
            report["top_products"], x="product", y="total_amount",
            labels={"product": "Product", "total_amount": "Revenue (Rs.)"},
            color="total_amount", color_continuous_scale="Greens",
        )
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sales recorded yet for this period. Try: *'I sold 12 coconuts for 900 rupees'* on the Chat page.")

with c2:
    st.subheader("💸 Expense Breakdown")
    if report["expense_breakdown"]:
        fig = px.pie(report["expense_breakdown"], names="category", values="amount", hole=0.5)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No expenses recorded yet for this period.")

st.markdown("<br/>", unsafe_allow_html=True)
st.subheader("📦 Inventory Snapshot")
if inventory["items"]:
    fig = px.bar(
        inventory["items"], x="product", y="quantity",
        color=[("Low stock" if i["quantity"] <= i["low_stock_threshold"] else "OK") for i in inventory["items"]],
        color_discrete_map={"Low stock": "#dc2626", "OK": "#16a34a"},
        labels={"quantity": "Quantity", "product": "Product", "color": "Status"},
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No inventory data yet. Record a few sales or 'stock purchase' expenses to populate this.")

if restock["low_stock"] or restock["fast_moving_low_runway"]:
    st.markdown('<div class="va-card">', unsafe_allow_html=True)
    st.markdown('<span class="va-badge">⚠️ Restock suggestions</span>', unsafe_allow_html=True)
    for item in restock["low_stock"]:
        st.write(f"- **{item['product']}** is at {item['quantity']} {item['unit']} (below threshold of {item['low_stock_threshold']}).")
    for item in restock["fast_moving_low_runway"]:
        st.write(
            f"- **{item['product']}** is selling fast (~{item['avg_daily_sales']}/day) "
            f"and may run out in ~{item['estimated_days_left']} days."
        )
    st.markdown("</div>", unsafe_allow_html=True)
