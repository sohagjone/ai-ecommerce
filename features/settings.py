import streamlit as st
from core import db
from core.config import DB_PATH, default_model, get_provider, has_api_key, provider_cfg


def render():
    st.title("Settings")
    st.subheader("AI configuration")
    if has_api_key(): st.success(f"{provider_cfg()['label']} API key detected (hidden). AI mode is on.")
    else: st.warning("No API key found, so the app runs in demo mode. Set GROQ_API_KEY in `.env` or Streamlit secrets.")
    model = st.text_input("AI model", st.session_state.get("model", default_model()), help="Any chat model your key can use, e.g. llama-3.3-70b-versatile or llama-3.1-8b-instant (Groq).")
    if st.button("Save model"):
        st.session_state["model"] = model.strip() or default_model(); db.set_setting("model", st.session_state["model"]); st.success("Saved.")
    st.subheader("Data")
    st.caption(f"Local database: `{DB_PATH}` (on Streamlit Community Cloud this storage is temporary).")
    st.caption("Live marketplace data is never scraped. Optional data APIs must be configured and authorised by you.")
    if st.checkbox("I understand this deletes all analysed products and niches") and st.button("Delete all data", type="primary"):
        db.clear_all(); st.session_state.clear(); st.success("All data deleted.")
