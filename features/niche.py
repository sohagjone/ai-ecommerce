import pandas as pd
import plotly.express as px
import streamlit as st
from core import ai, db
from core.config import has_api_key
from core.data import clean_text
from core.ui import BADGE, mode_banner, score_breakdown


def render():
    st.title("Niche Research")
    use_ai = has_api_key()
    mode_banner(use_ai)
    with st.form("niche"):
        a, b = st.columns([3, 1])
        topic = a.text_input("Topic or keywords (optional)", placeholder="e.g. pets, fitness, home")
        n = b.slider("Niches", 3, 8, 5)
        go = st.form_submit_button("🧭 Analyse niches", type="primary")
    if go:
        try:
            with st.spinner("Analysing…"):
                res, mode = ai.find_niches(clean_text(topic, 80), n, st.session_state.get("model"), use_ai)
        except ai.AIError as e:
            st.error(str(e)); return
        db.add_niches(res); st.session_state["niches"] = (res, mode)
    if "niches" not in st.session_state:
        st.write("Run an analysis to rank niches with a transparent 100-point score."); return
    res, mode = st.session_state["niches"]
    st.subheader("Ranking · " + ("AI estimates" if mode == "ai" else "sample data"))
    df = pd.DataFrame([{"Niche": r["name"], "Score": r["score"], "Demand": r["demand"], "Growth": r["growth"], "Competition": r["competition"],
                        "Avg price": r["avg_price"], "Margin %": r["margin_pct"], "Seasonal stability": r["seasonality"], "Entry barrier": r["entry_barrier"]} for r in res])
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d")})
    st.plotly_chart(px.scatter(df, x="Competition", y="Demand", size="Score", color="Margin %", text="Niche", title="Demand vs competition (bubble = score)",
                               range_x=[0, 10.5], range_y=[0, 10.5]).update_traces(textposition="top center"), use_container_width=True)
    for r in res:
        with st.expander(f"{r['name']} · {r['score']}/100 ({BADGE.get(r.get('data_label'), '')})"):
            st.markdown(f"**Customer pain points:** {r.get('pain_points') or 'n/a'}")
            if r.get("reasoning"): st.markdown(f"**AI reasoning:** {r['reasoning']}")
            score_breakdown(r["breakdown"])
            st.caption("Seasonal stability: 10 = demand stays steady all year. Entry barrier: 10 = very hard to enter. Values are estimates.")
