import streamlit as st
from core import db
from core.reports import build_csv, build_excel, build_pdf, summary_text
from core.scoring import finance


def render():
    st.title("Reports & Exports")
    saved, allp = db.list_products(saved_only=True), db.list_products()
    if not allp:
        st.info("Analyse or save some products first (Overview has a one-click sample dataset)."); return
    title = st.text_input("Report title", "E-commerce Opportunity Report")
    scope = st.radio("Products to include", ["Saved products", "All analysed products", "Top 10 by score"], horizontal=True)
    recs = saved if scope == "Saved products" else allp if scope == "All analysed products" else sorted(allp, key=lambda r: -r.get("score", 0))[:10]
    inc_n = st.checkbox("Include niche analysis", True); inc_c = st.checkbox("Include latest profit calculation", True)
    if not recs:
        st.warning("No products in this selection. Save some products or pick another scope."); return
    niches = db.list_niches(limit=8) if inc_n else []
    calc = st.session_state.get("calc") if inc_c else None
    st.write(summary_text(recs, niches))
    a, b, c = st.columns(3)
    try:
        a.download_button("📄 PDF report", build_pdf(title, recs, niches, calc), "report.pdf", "application/pdf")
        b.download_button("📊 Excel workbook", build_excel(title, recs, niches, calc), "report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        c.download_button("🧾 CSV", build_csv(recs), "products.csv", "text/csv")
    except Exception as e:
        st.error(f"Could not build the report ({type(e).__name__}).")
    st.caption("Exports never include API keys. Estimates are labelled by data source.")
