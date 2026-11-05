import io, os, sys, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
[os.environ.pop(k, None) for k in ("OPENAI_API_KEY", "GROQ_API_KEY")]
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
from core import ai, db
from core.calc import calculate_profit
from core.data import load_sample, read_upload, safe_cell, validate_dataframe
from core.reports import build_csv, build_excel, build_pdf
from core.scoring import niche_score, opportunity_score


class Up(io.BytesIO):
    def __init__(self, b, name): super().__init__(b); self.name = name; self.size = len(b)


def test_profit_known_example():
    r = calculate_profit(15, 50, 5, 10, 0, 1, 5, 1, 30)
    assert (r["total_cost"], r["net_profit"], r["margin_pct"], r["roi_pct"]) == (32, 18, 36, 56.25)
    assert r["break_even_price"] == 30 and r["max_sourcing_cost"] == 18 and r["gross_profit"] == 29


def test_zero_price_safe():
    assert calculate_profit(5, 0)["margin_pct"] == 0


def test_scores_in_range():
    for r in load_sample():
        assert 0 <= opportunity_score(r)["score"] <= 100
    assert 0 <= niche_score(ai.DEMO_NICHES[0])[0] <= 100


def test_csv_upload_valid_and_invalid():
    ok = b"Product,Price,Cost\nA,20,5\nB,abc,5\n,10,2\nC,10,-1\n"
    recs, errs, warns = read_upload(Up(ok, "x.csv"))
    assert len(recs) == 1 and len(errs) == 3 and warns
    assert read_upload(Up(b"a,b\n1,2\n", "x.csv"))[1][0].startswith("Missing required")
    assert read_upload(Up(b"zz", "x.txt"))[1]
    assert read_upload(Up(b"\x00\x01bad", "x.xlsx"))[1]


def test_excel_upload():
    b = io.BytesIO(); pd.DataFrame({"name": ["A"], "selling_price": [20], "sourcing_cost": [5], "demand": ["high"]}).to_excel(b, index=False)
    recs, errs, _ = read_upload(Up(b.getvalue(), "x.xlsx"))
    assert len(recs) == 1 and not errs and recs[0]["demand"] == 8


def test_db_and_exports():
    db.init_db(); db.clear_all()
    recs = db.add_products(load_sample(), saved=True)
    ns, mode = ai.find_niches("pet", 3, use_ai=False); db.add_niches(ns)
    calc = {"inputs": dict(name="x", price=50, sourcing=15, shipping=5, fee_pct=10, fixed_fee=0, packaging=1, advertising=5, other=1),
            "result": calculate_profit(15, 50, 5, 10, 0, 1, 5, 1, 30)}
    for r in recs: r["insight"] = ai.rule_insights(r, {**calculate_profit(r["sourcing_cost"], r["selling_price"], r["shipping_cost"], 15), "margin_pct": r["margin"]})
    assert db.stats()["products"] == 20 and db.stats()["niches"] == len(ns)
    pdf = build_pdf("T", recs[:6], ns, calc); assert pdf[:4] == b"%PDF"
    xl = build_excel("T", recs, ns, calc)
    sheets = pd.ExcelFile(io.BytesIO(xl)).sheet_names
    assert {"Summary", "Products", "Rankings", "Niches", "Profit calculation", "Risks", "Assumptions"} <= set(sheets)
    assert b"Product,Category" in build_csv(recs)
    assert safe_cell("=1+1").startswith("'")


def test_demo_discovery_filters():
    p = dict(category="pet", marketplace="Amazon US", min_price=10, max_price=40, min_margin=15, min_demand=5, max_competition=9, traits="", n=5)
    recs, mode = ai.discover_products(p, use_ai=False)
    assert mode == "sample" and recs and all("pet" in (r["name"] + r["category"]).lower() for r in recs)


def test_groq_provider_selected(monkeypatch):
    from core import config
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test"); monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert config.get_provider() == "groq" and "groq.com" in config.provider_cfg()["base_url"]
    assert config.default_model() == "llama-3.3-70b-versatile"
    assert ai._client().base_url.host == "api.groq.com"
    monkeypatch.delenv("GROQ_API_KEY"); assert config.get_provider() == "openai"
    monkeypatch.delenv("OPENAI_API_KEY"); assert config.get_provider() is None
