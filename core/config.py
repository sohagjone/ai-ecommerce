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
                 model_env="GROQ_MODEL", default_model="openai/gpt-oss-120b"),
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


# Groq models that were shut down, mapped to Groq's recommended replacements.
RETIRED_GROQ_MODELS = {
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b", "llama-3.1-8b-instant": "openai/gpt-oss-20b",
    "qwen/qwen3-32b": "openai/gpt-oss-120b", "meta-llama/llama-4-scout-17b-16e-instruct": "openai/gpt-oss-120b",
    "meta-llama/llama-4-maverick-17b-128e-instruct": "openai/gpt-oss-120b", "moonshotai/kimi-k2-instruct-0905": "openai/gpt-oss-120b",
}


def resolve_model(model):
    """Swap a retired Groq model name for its replacement so old .env/Settings values keep working."""
    if get_provider() == "groq":
        return RETIRED_GROQ_MODELS.get(model, model)
    return model


def default_model() -> str:
    cfg = provider_cfg() or {**PROVIDERS["groq"]}
    return resolve_model(os.getenv(cfg["model_env"]) or cfg["default_model"])


DEFAULT_MODEL = default_model()


def has_api_key() -> bool:
    return get_provider() is not None
