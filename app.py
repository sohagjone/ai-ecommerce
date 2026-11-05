"""AI E-commerce Product Finder - Streamlit entry point."""
import streamlit as st

st.set_page_config(page_title="AI E-commerce Product Finder", page_icon="🛒", layout="wide")

from core import db
from core.config import default_model, has_api_key
from core.ui import inject_css
from features import analyzer, calculator, comparison, discovery, niche, overview, reports_page, saved, settings

PAGES = {"📊 Overview": overview, "🔍 Product Discovery": discovery, "⚖️ Product Comparison": comparison, "🧭 Niche Research": niche,
         "🧮 Profit Calculator": calculator, "🔬 Resale Analyzer": analyzer, "⭐ Saved Products": saved, "📄 Reports & Exports": reports_page, "⚙️ Settings": settings}

db.init_db()
inject_css()
st.session_state.setdefault("model", db.get_setting("model", default_model()))
with st.sidebar:
    st.markdown("## 🛒 Product Finder")
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
    st.divider()
    st.caption("🤖 AI mode" if has_api_key() else "🧪 Demo mode (no API key)")
    st.caption("Estimates only. Not financial advice or a profit guarantee.")
PAGES[page].render()
