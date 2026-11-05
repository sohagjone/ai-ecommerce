"""Shared Streamlit UI helpers."""
import pandas as pd
import plotly.express as px
import streamlit as st

from . import db
from .config import has_api_key
from .data import load_sample
from .scoring import finance, opportunity_score, pros_cons

BADGE = {"ai": "🤖 AI estimate", "sample": "🧪 Sample data", "user": "✍️ User data", "verified": "✅ Verified"}
CSS = """<style>
.block-container{padding-top:2rem;max-width:1250px}
[data-testid=stMetric]{background:#f6f8fb;border:1px solid #e3e8ef;border-radius:12px;padding:.8rem 1rem}
[data-testid=stMetricLabel]{color:#52607a}
h1,h2,h3{letter-spacing:-.01em}
</style>"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def mode_banner(use_ai):
    if use_ai and has_api_key():
        st.caption("🤖 AI mode: results are **AI estimates**, not verified market data. Check them against real suppliers and marketplaces.")
    else:
        st.info("🧪 **Demo mode**: results come from a built-in illustrative sample dataset (no live market data). "
                "Add a `GROQ_API_KEY` to enable AI mode, or enter your own data.")


def money(x):
    return f"${x:,.2f}"


def record_row(r):
    f = finance(r)
    return {"Product": r["name"], "Category": r.get("category"), "Price": r["selling_price"], "Net profit": round(f["net_profit"], 2),
            "Margin %": round(f["margin_pct"], 1), "ROI %": round(f["roi_pct"]), "Score": r.get("score", opportunity_score(r)["score"]),
            "Source": BADGE.get(r.get("data_label"), r.get("data_label"))}


def results_table(recs):
    df = pd.DataFrame([record_row(r) for r in recs])
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
                                "Price": st.column_config.NumberColumn(format="$%.2f"), "Net profit": st.column_config.NumberColumn(format="$%.2f")})


def score_breakdown(rows):
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                 column_config={"Points": st.column_config.NumberColumn(format="%.1f")})


def product_detail(r, key, allow_save=True):
    """Expandable card for one product."""
    f = finance(r)
    with st.expander(f"{r['name']} · score {r.get('score', '?')}/100 · margin {f['margin_pct']:.0f}%  ({BADGE.get(r.get('data_label'), '')})"):
        if r.get("description"): st.write(r["description"])
        a, b, c, d = st.columns(4)
        a.metric("Selling price", money(r["selling_price"])); b.metric("Sourcing cost", money(r["sourcing_cost"]))
        c.metric("Net profit", money(f["net_profit"])); d.metric("ROI", f"{f['roi_pct']:.0f}%")
        for lab, k in (("Target customer", "target_customer"), ("Demand", "demand_assessment"), ("Competition", "competitive_landscape")):
            if r.get(k): st.markdown(f"**{lab}:** {r[k]}")
        if r.get("features"): st.markdown("**Features:** " + ", ".join(r["features"]))
        pros, cons = pros_cons(r, f)
        p1, p2 = st.columns(2)
        p1.markdown("**Pros**\n" + "\n".join(f"- {x}" for x in pros or ["n/a"])); p2.markdown("**Cons**\n" + "\n".join(f"- {x}" for x in cons or ["n/a"]))
        st.markdown("**How the score is built**"); score_breakdown(r.get("breakdown") or opportunity_score(r)["breakdown"])
        miss = (r.get("missing") or []) + (r.get("ai_missing") or [])
        if miss: st.warning("Missing information that could change this: " + "; ".join(miss))
        if r.get("assumptions"): st.caption("Assumptions: " + "; ".join(r["assumptions"]))
        if r.get("insight"):
            i = r["insight"]
            st.markdown(f"**Resale potential:** {i['resale_potential']}  \n**Channels:** {', '.join(i['channels'])}  \n**Pricing:** {i['pricing_strategy']}")
            st.markdown("**Risks:** " + "; ".join(i["risks"]))
        if allow_save and r.get("id"):
            if r.get("saved"): st.success("Saved")
            else: st.button("⭐ Save product", key=f"save_{key}_{r['id']}", on_click=db.set_saved, args=(r["id"], True))


def empty_state(title, text, button=None, key=None, action=None):
    st.markdown(f"#### {title}")
    st.write(text)
    if button and st.button(button, key=key):
        action()
        st.rerun()


def load_sample_into_db():
    db.add_products(load_sample("sample"))


def bar_scores(recs, title="Top opportunity scores"):
    df = pd.DataFrame({"Product": [r["name"] for r in recs], "Score": [r.get("score", 0) for r in recs]}).sort_values("Score")
    fig = px.bar(df, x="Score", y="Product", orientation="h", title=title, range_x=[0, 100], color="Score", color_continuous_scale="Blues")
    fig.update_layout(coloraxis_showscale=False, height=max(260, 36 * len(df) + 90), margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)
