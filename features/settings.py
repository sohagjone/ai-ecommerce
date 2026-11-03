import streamlit as st
from core import db
from core.config import DB_PATH, DEFAULT_MODEL, has_api_key


def render():
    st.title("Settings")
    st.subheader("AI configuration")
    if has_api_key(): st.success("OpenAI API key detected (hidden). AI mode is on.")
    else: st.warning("No API key found, so the app runs in demo mode. Set OPENAI_API_KEY in `.env` or Streamlit secrets.")
    model = st.text_input("OpenAI model", st.session_state.get("model", db.get_setting("model", DEFAULT_MODEL)), help="Any chat model your key can use, e.g. gpt-4o-mini or gpt-4o.")
    if st.button("Save model"):
        st.session_state["model"] = model.strip() or DEFAULT_MODEL; db.set_setting("model", st.session_state["model"]); st.success("Saved.")
    st.subheader("Data")
    st.caption(f"Local database: `{DB_PATH}` (on Streamlit Community Cloud this storage is temporary).")
    st.caption("Live marketplace data is never scraped. Optional data APIs must be configured and authorised by you.")
    if st.checkbox("I understand this deletes all analysed products and niches") and st.button("Delete all data", type="primary"):
        db.clear_all(); st.session_state.clear(); st.success("All data deleted.")
