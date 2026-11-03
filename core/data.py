"""Import, validation and sanitisation of product data."""
import io, re
import pandas as pd

from .config import MAX_UPLOAD_MB, MAX_UPLOAD_ROWS, SAMPLE_CSV

ALIASES = {
    "name": ["name", "product", "product_name", "title", "item"],
    "category": ["category", "niche", "department"],
    "selling_price": ["selling_price", "price", "sale_price", "sell_price", "retail_price"],
    "sourcing_cost": ["sourcing_cost", "cost", "unit_cost", "purchase_cost", "cogs", "buy_price", "sourcing_price"],
    "shipping_cost": ["shipping_cost", "shipping"],
    "fee_pct": ["fee_pct", "fees_pct", "marketplace_fee_pct", "fee_percent", "fees"],
    "demand": ["demand", "demand_score"], "competition": ["competition", "competition_level"],
    "rating": ["rating", "avg_rating", "stars"], "review_count": ["review_count", "reviews", "num_reviews"],
    "features": ["features", "key_features"], "target_customer": ["target_customer", "audience"],
    "description": ["description", "desc"],
}
LEVELS = {"very low": 1, "low": 2, "medium": 5, "moderate": 5, "high": 8, "very high": 9}
CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _blank(v):
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ""


def clean_text(s, maxlen=400):
    return "" if _blank(s) else CTRL.sub("", str(s)).strip()[:maxlen]


def _num(v):
    if _blank(v):
        return None
    try:
        return float(str(v).replace("$", "").replace(",", "").replace("%", "").strip())
    except ValueError:
        raise ValueError(f"'{v}' is not a number")


def _level(v):
    if _blank(v):
        return None
    s = str(v).strip().lower()
    if s in LEVELS:
        return LEVELS[s]
    return max(1.0, min(10.0, _num(v)))


def normalize_record(raw, label="user"):
    """Validate a dict into a clean product record; raises ValueError with a readable message."""
    name = clean_text(raw.get("name"), 120)
    if not name:
        raise ValueError("product name is missing")
    price, cost = _num(raw.get("selling_price")), _num(raw.get("sourcing_cost"))
    if price is None or price <= 0:
        raise ValueError("selling_price must be a number greater than 0")
    if cost is None or cost < 0:
        raise ValueError("sourcing_cost must be a number of 0 or more")
    ship, fee = _num(raw.get("shipping_cost")), _num(raw.get("fee_pct"))
    if (ship is not None and ship < 0) or (fee is not None and not 0 <= fee < 100):
        raise ValueError("shipping_cost must be >= 0 and fee_pct between 0 and 99")
    rating, rc = _num(raw.get("rating")), _num(raw.get("review_count"))
    if rating is not None and not 0 <= rating <= 5:
        raise ValueError("rating must be between 0 and 5")
    feats = raw.get("features")
    feats = [] if _blank(feats) else feats
    if isinstance(feats, str):
        feats = [f.strip() for f in re.split(r"[;|]", feats) if f.strip()]
    return {
        "name": name, "category": clean_text(raw.get("category"), 80) or "Uncategorised",
        "description": clean_text(raw.get("description"), 500), "target_customer": clean_text(raw.get("target_customer"), 200),
        "selling_price": price, "sourcing_cost": cost, "shipping_cost": ship, "fee_pct": fee,
        "demand": _level(raw.get("demand")), "competition": _level(raw.get("competition")),
        "rating": rating, "review_count": int(rc) if rc is not None else None,
        "features": [clean_text(f, 100) for f in feats][:10],
        "pros": [clean_text(x, 150) for x in (raw.get("pros") or [])][:6],
        "cons": [clean_text(x, 150) for x in (raw.get("cons") or [])][:6],
        "data_label": label,
    }


def standardize_columns(df):
    lookup = {a: k for k, al in ALIASES.items() for a in al}
    df = df.rename(columns={c: lookup.get(re.sub(r"[\s\-]+", "_", str(c).strip().lower()), c) for c in df.columns})
    return df.loc[:, ~df.columns.duplicated()]


def validate_dataframe(df, label="user"):
    """Returns (records, errors, warnings)."""
    errors, warnings, records = [], [], []
    df = standardize_columns(df)
    miss = [c for c in ("name", "selling_price", "sourcing_cost") if c not in df.columns]
    if miss:
        return [], [f"Missing required column(s): {', '.join(miss)}. Found: {', '.join(map(str, df.columns)) or 'none'}."], []
    if len(df) == 0:
        return [], ["The file has no data rows."], []
    if len(df) > MAX_UPLOAD_ROWS:
        warnings.append(f"Only the first {MAX_UPLOAD_ROWS} rows were used.")
        df = df.head(MAX_UPLOAD_ROWS)
    for i, row in df.iterrows():
        try:
            records.append(normalize_record(row.to_dict(), label))
        except ValueError as e:
            errors.append(f"Row {i + 2}: {e}")
    if not records:
        errors.insert(0, "No valid rows were found.")
    elif errors:
        warnings.append(f"{len(errors)} invalid row(s) were skipped.")
    return records, errors, warnings


def read_upload(file):
    """Read an uploaded CSV/Excel file. Returns (records, errors, warnings)."""
    name = file.name.lower()
    if file.size > MAX_UPLOAD_MB * 1024 * 1024:
        return [], [f"File is larger than {MAX_UPLOAD_MB} MB."], []
    try:
        raw = file.getvalue()
        if name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw))
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(raw))
        else:
            return [], ["Unsupported file type. Upload a .csv or .xlsx file."], []
    except Exception as e:
        return [], [f"Could not read the file ({type(e).__name__}). Check that it is a valid CSV/Excel file."], []
    return validate_dataframe(df, "user")


def load_sample(label="sample"):
    recs, errs, _ = validate_dataframe(pd.read_csv(SAMPLE_CSV), label)
    assert not errs, errs
    return recs


def safe_cell(v):
    """Neutralise spreadsheet formula injection in exports."""
    return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v
