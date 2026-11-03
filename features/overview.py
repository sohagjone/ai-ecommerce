import streamlit as st
from core import db
from core.ui import bar_scores, empty_state, load_sample_into_db, results_table


def render():
    st.title("Overview")
    s, recs = db.stats(), db.list_products()
    if not recs:
        empty_state("Welcome 👋", "Nothing analysed yet. Discover products, import your own list, or load the sample dataset to explore the app.",
                    "Load sample dataset", "ov_sample", load_sample_into_db)
        return
    best = max(recs, key=lambda r: r.get("score", 0))
    c = st.columns(4)
    c[0].metric("Products analysed", s["products"]); c[1].metric("Avg. est. margin", f"{s['avg_margin']:.1f}%")
    c[2].metric("Top opportunity", f"{best.get('score', 0)}/100", best["name"][:28]); c[3].metric("Niches researched", s["niches"])
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Recently analysed"); results_table(recs[:8])
    with right:
        bar_scores(sorted(recs, key=lambda r: -r.get("score", 0))[:6])
    st.caption("All margins and scores are estimates based on the data entered or generated; they are not guarantees.")
