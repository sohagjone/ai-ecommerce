import streamlit as st
from core import ai, db
from core.config import DB_PATH, default_model, get_provider, has_api_key, provider_cfg


def render():
    st.title("Settings")
    st.subheader("AI configuration")
    if has_api_key(): st.success(f"{provider_cfg()['label']} API key detected (hidden). AI mode is on.")
    else: st.warning("No API key found, so the app runs in demo mode. Set GROQ_API_KEY in `.env` or Streamlit secrets.")
    cur = st.session_state.get("model", default_model())
    if has_api_key() and st.button("Load available models"):
        try:
            st.session_state["model_list"] = ai.available_models()
        except Exception as e:
            st.error(f"Could not load models ({type(e).__name__}). Check your key and connection.")
    models = st.session_state.get("model_list")
    if models:
        model = st.selectbox("AI model", models, index=models.index(cur) if cur in models else 0)
    else:
        model = st.text_input("AI model", cur, help="Groq default: openai/gpt-oss-120b. Click 'Load available models' to see what your key can use.")
    if st.button("Save model"):
        st.session_state["model"] = model.strip() or default_model(); db.set_setting("model", st.session_state["model"]); st.success("Saved.")
    st.subheader("Data")
    st.caption(f"Local database: `{DB_PATH}` (on Streamlit Community Cloud this storage is temporary).")
    st.caption("Live marketplace data is never scraped. Optional data APIs must be configured and authorised by you.")
    if st.checkbox("I understand this deletes all analysed products and niches") and st.button("Delete all data", type="primary"):
        db.clear_all(); st.session_state.clear(); st.success("All data deleted.")
