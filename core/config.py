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
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
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


def has_api_key() -> bool:
    return bool(get_secret("OPENAI_API_KEY"))
