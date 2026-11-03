import streamlit as st
from core import ai, db
from core.config import MARKETPLACES, has_api_key
from core.data import clean_text
from core.ui import mode_banner, product_detail, results_table


def render():
    st.title("Product Discovery")
    use_ai = has_api_key()
    mode_banner(use_ai)
    with st.form("discover"):
        a, b, c = st.columns(3)
        category = a.text_input("Category / niche", placeholder="e.g. home office, pets, kitchen")
        market = b.selectbox("Target marketplace", MARKETPLACES)
        n = c.slider("Number of ideas", 3, 10, 5)
        a, b, c, d = st.columns(4)
        pmin = a.number_input("Min selling price ($)", 0.0, 10000.0, 10.0); pmax = b.number_input("Max selling price ($)", 1.0, 10000.0, 60.0)
        margin = c.slider("Min net margin %", 0, 60, 15); demand = d.slider("Min demand (1-10)", 1, 10, 5)
        a, b = st.columns(2)
        comp = a.slider("Max competition (1-10)", 1, 10, 8)
        traits = b.text_input("Characteristics / trends", placeholder="lightweight, eco-friendly, giftable…")
        go = st.form_submit_button("🔍 Discover products", type="primary")
    if go:
        if pmin > pmax:
            st.error("Minimum price must not exceed maximum price."); return
        p = dict(category=clean_text(category, 80), marketplace=market, min_price=pmin, max_price=pmax, min_margin=margin,
                 min_demand=demand, max_competition=comp, traits=clean_text(traits, 120), n=n)
        try:
            with st.spinner("Analysing…"):
                recs, mode = ai.discover_products(p, st.session_state.get("model"), use_ai)
        except ai.AIError as e:
            st.error(str(e)); return
        if not recs:
            st.warning("No products matched these criteria in the sample dataset. Relax the filters or add an API key for AI mode."); return
        st.session_state["disc"] = (db.add_products(recs), mode)
    if st.session_state.get("disc"):
        recs, mode = st.session_state["disc"]
        st.subheader(f"Results ({'AI estimates' if mode == 'ai' else 'sample data'})")
        results_table(recs)
        for r in recs:
            product_detail(r, "disc")
