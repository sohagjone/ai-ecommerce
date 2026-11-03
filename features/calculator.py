import plotly.graph_objects as go
import streamlit as st
from core import db
from core.calc import calculate_profit
from core.config import DEFAULT_FEE_PCT
from core.ui import money


def render():
    st.title("Resale Profit Calculator")
    L, R = st.columns([2, 3])
    with L:
        name = st.text_input("Product name (optional)", "My product")
        price = st.number_input("Selling price ($)", 0.0, 1e6, 29.99, 0.5)
        sourcing = st.number_input("Purchase / sourcing cost ($)", 0.0, 1e6, 9.00, 0.5)
        shipping = st.number_input("Shipping cost ($)", 0.0, 1e6, 3.00, 0.5)
        a, b = st.columns(2)
        fee = a.number_input("Marketplace fee (%)", 0.0, 99.0, DEFAULT_FEE_PCT, 0.5); fixed = b.number_input("Fixed fee per sale ($)", 0.0, 1e4, 0.0, 0.1)
        packaging = a.number_input("Packaging ($)", 0.0, 1e4, 0.50, 0.1); ads = b.number_input("Advertising per sale ($)", 0.0, 1e4, 2.00, 0.5)
        other = a.number_input("Other expenses ($)", 0.0, 1e4, 0.0, 0.1); target = b.number_input("Target net margin (%)", 0.0, 95.0, 25.0, 1.0)
    r = calculate_profit(sourcing, price, shipping, fee, fixed, packaging, ads, other, target)
    st.session_state["calc"] = {"inputs": dict(name=name, price=price, sourcing=sourcing, shipping=shipping, fee_pct=fee, fixed_fee=fixed, packaging=packaging, advertising=ads, other=other), "result": r}
    with R:
        a, b, c = st.columns(3)
        a.metric("Net profit", money(r["net_profit"])); b.metric("Net margin", f"{r['margin_pct']:.1f}%"); c.metric("ROI", f"{r['roi_pct']:.1f}%")
        a, b, c = st.columns(3)
        a.metric("Total cost", money(r["total_cost"])); b.metric("Gross profit", money(r["gross_profit"]), help="Price minus sourcing, shipping and packaging")
        c.metric("Break-even price", money(r["break_even_price"]) if r["break_even_price"] != float("inf") else "n/a")
        st.metric(f"Max sourcing cost for {target:.0f}% margin", money(r["max_sourcing_cost"]))
        if r["net_profit"] < 0: st.error("This setup loses money per sale.")
        elif r["margin_pct"] < target: st.warning(f"Margin is below your {target:.0f}% target. Lower sourcing to {money(r['max_sourcing_cost'])} or raise the price.")
        else: st.success("Meets your target margin.")
        parts = {"Sourcing": sourcing, "Shipping": shipping, "Fees": r["fees"], "Packaging": packaging, "Advertising": ads, "Other": other, "Net profit": max(r["net_profit"], 0)}
        st.plotly_chart(go.Figure(go.Pie(labels=list(parts), values=list(parts.values()), hole=.5)).update_layout(title="Where the selling price goes", height=340), use_container_width=True)
    if price > 0 and st.button("⭐ Save as product"):
        db.add_products([dict(name=name or "Calculator product", category="Calculator", selling_price=price, sourcing_cost=sourcing, shipping_cost=shipping, fee_pct=fee, advertising_cost=ads,
                              demand=None, competition=None, rating=None, review_count=None, features=[], data_label="user")], saved=True)
        st.success("Saved. Find it under Saved Products.")
