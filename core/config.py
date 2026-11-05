"""Central configuration. Secrets come from env vars or Streamlit secrets only."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("DB_PATH", str(ROOT / "data" / "app.db"))
SAMPLE_CSV = ROOT / "data" / "sample_products.csv"
DEFAULT_FEE_PCT = 12.0
MARKETPLACES = ["Amazon US", "Amazon UK", "Amazon DE", "eBay", "Etsy", "Walmart",
                "Shopify / own store", "TikTok Shop", "Other"]
MAX_UPLOAD_MB = 5
MAX_UPLOAD_ROWS = 500


def get_secret(name, default=None):
    """Read a secret from the environment first, then Streamlit secrets."""
    val = os.getenv(name)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return default


PROVIDERS = {
    "groq": dict(label="Groq", key="GROQ_API_KEY", base_url="https://api.groq.com/openai/v1",
                 model_env="GROQ_MODEL", default_model="llama-3.3-70b-versatile"),
    "openai": dict(label="OpenAI", key="OPENAI_API_KEY", base_url=None,
                   model_env="OPENAI_MODEL", default_model="gpt-4o-mini"),
}


def get_provider():
    """Groq takes priority when GROQ_API_KEY is set; OpenAI is an optional fallback. None = demo mode."""
    for name, cfg in PROVIDERS.items():
        if get_secret(cfg["key"]):
            return name
    return None


def provider_cfg():
    name = get_provider()
    return {**PROVIDERS[name], "name": name, "api_key": get_secret(PROVIDERS[name]["key"])} if name else None


def default_model() -> str:
    cfg = provider_cfg() or {**PROVIDERS["groq"]}
    return os.getenv(cfg["model_env"]) or cfg["default_model"]


DEFAULT_MODEL = default_model()


def has_api_key() -> bool:
    return get_provider() is not None
