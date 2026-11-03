import pandas as pd
import streamlit as st
from core import ai, db
from core.config import DEFAULT_FEE_PCT, has_api_key
from core.data import load_sample, normalize_record, read_upload
from core.scoring import finance
from core.ui import product_detail, results_table

TEMPLATE = "name,category,selling_price,sourcing_cost,shipping_cost,fee_pct,demand,competition,rating,review_count\nExample Item,Kitchen,24.99,6.50,2.00,15,7,5,4.4,1200\n"


def _analyse(recs, label_msg, use_ai):
    out = db.add_products(recs)
    ins = {}
    if use_ai and has_api_key():
        try:
            with st.spinner("Running AI analysis…"):
                ins = ai.ai_insights(out, st.session_state.get("model"))
        except ai.AIError as e:
            st.warning(f"{e} Showing rule-based insights instead.")
    for r in out:
        r["insight"] = ins.get(r["name"]) or ai.rule_insights(r, finance(r))
    st.session_state["analysis"] = out
    st.success(label_msg)


def render():
    st.title("Resale Opportunity Analyzer")
    use_ai = st.toggle("Add AI narrative (needs API key)", value=has_api_key(), disabled=not has_api_key())
    tab1, tab2, tab3 = st.tabs(["Manual entry", "Upload CSV / Excel", "Sample dataset"])
    with tab1:
        with st.form("manual"):
            a, b, c = st.columns(3)
            name = a.text_input("Product name"); cat = b.text_input("Category"); price = c.number_input("Selling price ($)", 0.0, 1e6, 0.0)
            cost = a.number_input("Sourcing cost ($)", 0.0, 1e6, 0.0); ship = b.number_input("Shipping ($)", 0.0, 1e6, 0.0); fee = c.number_input("Marketplace fee %", 0.0, 99.0, DEFAULT_FEE_PCT)
            dem = a.slider("Demand (1-10)", 1, 10, 5); comp = b.slider("Competition (1-10)", 1, 10, 5)
            go = st.form_submit_button("Analyse product", type="primary")
        if go:
            try:
                rec = normalize_record(dict(name=name, category=cat, selling_price=price, sourcing_cost=cost, shipping_cost=ship, fee_pct=fee, demand=dem, competition=comp), "user")
                _analyse([rec], "Product analysed.", use_ai)
            except ValueError as e:
                st.error(f"Please fix: {e}.")
    with tab2:
        st.download_button("Download CSV template", TEMPLATE, "product_template.csv", "text/csv")
        st.caption("Required columns: name, selling_price, sourcing_cost. Optional: category, shipping_cost, fee_pct, demand, competition, rating, review_count, features.")
        up = st.file_uploader("Upload a .csv or .xlsx file", type=["csv", "xlsx", "xls"])
        if up and st.button("Analyse file", type="primary"):
            recs, errs, warns = read_upload(up)
            for w in warns: st.warning(w)
            if errs:
                with st.expander(f"{len(errs)} problem(s) found", expanded=not recs):
                    for e in errs[:30]: st.write("• " + e)
            if recs: _analyse(recs, f"Analysed {len(recs)} product(s).", use_ai)
    with tab3:
        st.write("Analyse 20 illustrative sample products (not live market data).")
        if st.button("Analyse sample dataset"): _analyse(load_sample("sample"), "Sample dataset analysed.", use_ai)
    recs = st.session_state.get("analysis")
    if recs:
        recs = sorted(recs, key=lambda r: -r["score"])
        st.subheader("Results"); results_table(recs)
        st.download_button("Download results (CSV)", pd.DataFrame([{k: r[k] for k in ("name", "category", "selling_price", "sourcing_cost", "score", "margin")} for r in recs]).to_csv(index=False), "analysis.csv", "text/csv")
        for r in recs[:15]: product_detail(r, "an")
