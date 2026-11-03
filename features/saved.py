import streamlit as st
from core import db
from core.reports import build_csv
from core.ui import empty_state, product_detail, results_table


def render():
    st.title("Saved Products")
    recs = db.list_products(saved_only=True)
    if not recs:
        st.info("No saved products yet. Use the ⭐ Save button in Discovery, the Analyzer, or the Calculator."); return
    results_table(recs)
    st.download_button("Download CSV", build_csv(recs), "saved_products.csv", "text/csv")
    for r in recs:
        product_detail(r, "sv", allow_save=False)
        a, b, _ = st.columns([1, 1, 6])
        a.button("Unsave", key=f"u{r['id']}", on_click=db.set_saved, args=(r["id"], False))
        b.button("Delete", key=f"d{r['id']}", on_click=db.delete_product, args=(r["id"],))
