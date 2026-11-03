import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core import db
from core.data import load_sample
from core.scoring import finance, opportunity_score, pros_cons
from core.ui import BADGE


def _pool():
    pool = {}
    for r in db.list_products():
        pool[f"{r['name']} (#{r['id']})"] = r
    for r in load_sample("sample"):
        r.update({k: v for k, v in opportunity_score(r).items() if k in ("score", "breakdown", "missing")})
        pool.setdefault(f"{r['name']} · sample", r)
    return pool


def render():
    st.title("Product Comparison")
    pool = _pool()
    default = [k for k in pool if k.endswith("· sample")][:3]
    picks = st.multiselect("Choose 2-5 products", list(pool), default=default, max_selections=5)
    if len(picks) < 2:
        st.info("Select at least two products to compare."); return
    recs = [pool[k] for k in picks]
    fins = [finance(r) for r in recs]
    rows = {"Category": [r.get("category") for r in recs], "Selling price": [r["selling_price"] for r in recs], "Sourcing cost": [r["sourcing_cost"] for r in recs],
            "Shipping": [r.get("shipping_cost") or 0 for r in recs], "Marketplace fees": [round(f["fees"], 2) for f in fins],
            "Gross profit": [round(f["gross_profit"], 2) for f in fins], "Net profit": [round(f["net_profit"], 2) for f in fins],
            "Net margin %": [round(f["margin_pct"], 1) for f in fins], "ROI %": [round(f["roi_pct"]) for f in fins],
            "Rating": [r.get("rating") if r.get("rating") is not None else "n/a" for r in recs],
            "Reviews": [r.get("review_count") if r.get("review_count") is not None else "n/a" for r in recs],
            "Competition /10": [r.get("competition") if r.get("competition") is not None else "n/a" for r in recs],
            "Features": [", ".join(r.get("features") or []) or "n/a" for r in recs],
            "Pros": ["; ".join(pros_cons(r, f)[0]) or "n/a" for r, f in zip(recs, fins)], "Cons": ["; ".join(pros_cons(r, f)[1]) or "n/a" for r, f in zip(recs, fins)],
            "Opportunity score": [r.get("score", opportunity_score(r)["score"]) for r in recs], "Data source": [BADGE.get(r.get("data_label"), "") for r in recs]}
    df = pd.DataFrame(rows, index=[r["name"] for r in recs]).T.astype(str)
    st.dataframe(df, use_container_width=True)

    names = [r["name"] for r in recs]
    cost = pd.DataFrame({"Product": names * 3, "Amount": [r["sourcing_cost"] for r in recs] + [f["fees"] for f in fins] + [f["net_profit"] for f in fins],
                         "Part of price": ["Sourcing"] * len(recs) + ["Fees"] * len(recs) + ["Net profit"] * len(recs)})
    a, b = st.columns(2)
    a.plotly_chart(px.bar(cost, x="Product", y="Amount", color="Part of price", title="Where the selling price goes (excl. shipping)"), use_container_width=True)
    b.plotly_chart(px.bar(x=names, y=[f["margin_pct"] for f in fins], labels={"x": "", "y": "Net margin %"}, title="Net margin %"), use_container_width=True)
    fig = go.Figure()
    for r in recs:
        bd = r.get("breakdown") or opportunity_score(r)["breakdown"]
        fig.add_trace(go.Scatterpolar(r=[x["Points"] / x["Max"] * 100 for x in bd], theta=[x["Criterion"] for x in bd], fill="toself", name=r["name"]))
    fig.update_layout(title="Score components (% of maximum)", polar=dict(radialaxis=dict(range=[0, 100])))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Best product by strategy")
    best = lambda key, rev=True: names[sorted(range(len(recs)), key=key, reverse=rev)[0]]
    st.table(pd.DataFrame({"Strategy": ["Highest margin", "Fastest ROI / lowest capital risk", "Best demand vs. competition", "Best overall opportunity"],
                           "Best fit": [best(lambda i: fins[i]["margin_pct"]), best(lambda i: recs[i]["sourcing_cost"], False),
                                        best(lambda i: (recs[i].get("demand") or 5) - (recs[i].get("competition") or 5)), best(lambda i: rows["Opportunity score"][i])]}))
