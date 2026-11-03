"""AI layer (OpenAI) with a deterministic, clearly-labelled demo mode when no key is configured."""
import json, re, time

from .config import DEFAULT_MODEL, get_secret, has_api_key
from .data import clean_text, load_sample, normalize_record
from .scoring import finance, niche_score

SYSTEM = (
    "You are a cautious e-commerce research analyst. Rules: never invent product URLs, supplier names, customer "
    "reviews, ratings or live prices; every number you give is an ESTIMATE based on general market knowledge, not "
    "verified data; list assumptions and missing information; never guarantee profit or demand. "
    "Respond with a single valid JSON object only."
)


class AIError(Exception):
    """Raised with a user-friendly message."""


def _client():
    from openai import OpenAI
    return OpenAI(api_key=get_secret("OPENAI_API_KEY"), timeout=60)


def call_json(prompt, model=None, retries=3):
    if not has_api_key():
        raise AIError("No OpenAI API key configured. Running in demo mode.")
    import openai
    delay = 2
    for attempt in range(retries):
        try:
            r = _client().chat.completions.create(
                model=model or DEFAULT_MODEL, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}])
            txt = r.choices[0].message.content or "{}"
            return json.loads(re.sub(r"^```(?:json)?|```$", "", txt.strip()))
        except openai.RateLimitError:
            if attempt == retries - 1:
                raise AIError("OpenAI rate limit reached. Wait a minute and try again.")
            time.sleep(delay); delay *= 2
        except openai.AuthenticationError:
            raise AIError("The OpenAI API key was rejected. Check OPENAI_API_KEY.")
        except openai.NotFoundError:
            raise AIError(f"Model '{model or DEFAULT_MODEL}' was not found for this key. Change it in Settings.")
        except (openai.APIConnectionError, openai.APITimeoutError):
            if attempt == retries - 1:
                raise AIError("Could not reach OpenAI. Check your connection and try again.")
            time.sleep(delay); delay *= 2
        except openai.APIError as e:
            raise AIError(f"OpenAI API error: {getattr(e, 'message', type(e).__name__)[:200]}")
        except json.JSONDecodeError:
            if attempt == retries - 1:
                raise AIError("The AI returned an unreadable response. Please try again.")


# ---------------------------------------------------------------- product discovery
def discover_products(p, model=None, use_ai=True):
    """p: dict(category, marketplace, min_price, max_price, min_margin, min_demand, max_competition, traits, n).
    Returns (records, mode) where mode is 'ai' or 'sample'."""
    if use_ai and has_api_key():
        prompt = f"""Suggest {p['n']} product ideas for an online reseller.
Niche/category: {p['category'] or 'any'}; marketplace/country: {p['marketplace']}; selling price {p['min_price']}-{p['max_price']} USD;
target net margin >= {p['min_margin']}%; minimum demand {p['min_demand']}/10; maximum competition {p['max_competition']}/10; traits: {p['traits'] or 'none'}.
Return JSON {{"products":[{{"name","category","description","target_customer","selling_price","sourcing_cost","shipping_cost",
"fee_pct","demand"(1-10),"competition"(1-10),"features":[],"pros":[],"cons":[],"demand_assessment","competitive_landscape",
"assumptions":[],"missing_info":[]}}]}}. All numbers are estimates in USD per unit."""
        out = []
        for raw in (call_json(prompt, model) or {}).get("products", [])[: p["n"]]:
            try:
                rec = normalize_record(raw, "ai")
            except (ValueError, AttributeError):
                continue
            for k in ("demand_assessment", "competitive_landscape"):
                rec[k] = clean_text(raw.get(k), 400)
            rec["assumptions"] = [clean_text(a, 200) for a in (raw.get("assumptions") or [])][:6]
            rec["ai_missing"] = [clean_text(a, 200) for a in (raw.get("missing_info") or [])][:6]
            out.append(rec)
        if not out:
            raise AIError("The AI did not return usable product ideas. Try broader criteria.")
        return out, "ai"
    kw = (p["category"] or "").lower().split()
    out = []
    for r in load_sample("sample"):
        f = finance(r)
        text = f"{r['name']} {r['category']} {' '.join(r['features'])}".lower()
        if kw and not any(k in text for k in kw): continue
        if not p["min_price"] <= r["selling_price"] <= p["max_price"]: continue
        if f["margin_pct"] < p["min_margin"] or (r["demand"] or 0) < p["min_demand"] or (r["competition"] or 0) > p["max_competition"]: continue
        r["demand_assessment"] = f"Sample demand indicator {r['demand']}/10 (illustrative, not live data)."
        r["competitive_landscape"] = f"Sample competition indicator {r['competition']}/10 (illustrative)."
        out.append(r)
    out.sort(key=lambda r: -(finance(r)["margin_pct"] * 0.5 + (r["demand"] or 0) * 3 - (r["competition"] or 0) * 2))
    return out[: p["n"]], "sample"


# ---------------------------------------------------------------- niches
DEMO_NICHES = [
    dict(name="Eco-friendly kitchen", demand=7, growth=7, competition=6, differentiation=6, avg_price=22, margin_pct=32, seasonality=8, entry_barrier=3, pain_points="Plastic waste guilt; items that leak or stain"),
    dict(name="Home office ergonomics", demand=8, growth=6, competition=7, differentiation=6, avg_price=38, margin_pct=28, seasonality=8, entry_barrier=4, pain_points="Back/neck pain; cluttered small desks"),
    dict(name="Pet wellness & accessories", demand=8, growth=7, competition=7, differentiation=7, avg_price=27, margin_pct=30, seasonality=9, entry_barrier=4, pain_points="Hair/odour management; anxious or picky pets"),
    dict(name="Travel organisation", demand=7, growth=6, competition=8, differentiation=5, avg_price=26, margin_pct=29, seasonality=5, entry_barrier=3, pain_points="Overpacking; airline weight limits"),
    dict(name="Baby & parenting helpers", demand=6, growth=5, competition=5, differentiation=7, avg_price=22, margin_pct=33, seasonality=9, entry_barrier=7, pain_points="Safety worries; sleep and feeding routines"),
    dict(name="Indoor gardening", demand=6, growth=7, competition=5, differentiation=7, avg_price=28, margin_pct=34, seasonality=5, entry_barrier=3, pain_points="Limited space and light; plant care knowledge"),
    dict(name="Smart home starters", demand=8, growth=7, competition=9, differentiation=4, avg_price=27, margin_pct=22, seasonality=7, entry_barrier=5, pain_points="Compatibility confusion; setup difficulty"),
    dict(name="Home fitness accessories", demand=8, growth=5, competition=9, differentiation=4, avg_price=22, margin_pct=26, seasonality=6, entry_barrier=3, pain_points="Small spaces; motivation and progress tracking"),
]


def _finish_niche(n, label):
    n = {**n, "data_label": label, "name": clean_text(n["name"], 80), "pain_points": clean_text(n.get("pain_points"), 300)}
    n["score"], n["breakdown"] = niche_score(n)
    return n


def find_niches(topic, n=5, model=None, use_ai=True):
    if use_ai and has_api_key():
        prompt = f"""Analyse {n} e-commerce niches related to: "{topic or 'general consumer products'}".
Return JSON {{"niches":[{{"name","demand"(1-10),"growth"(1-10),"competition"(1-10),"differentiation"(1-10 room to differentiate),
"avg_price"(USD),"margin_pct"(typical net margin %),"seasonality"(1-10, 10=year-round stable),"entry_barrier"(1-10, 10=very hard),
"pain_points","reasoning"}}]}}. All values are estimates."""
        out = []
        for raw in (call_json(prompt, model) or {}).get("niches", [])[:n]:
            try:
                nn = {k: float(raw[k]) for k in ("demand", "growth", "competition", "differentiation", "avg_price", "margin_pct", "seasonality", "entry_barrier")}
                nn.update(name=raw["name"], pain_points=raw.get("pain_points", ""))
            except (KeyError, TypeError, ValueError):
                continue
            nn = _finish_niche(nn, "ai"); nn["reasoning"] = clean_text(raw.get("reasoning"), 400); out.append(nn)
        if not out:
            raise AIError("The AI did not return usable niches. Try a different topic.")
        return sorted(out, key=lambda x: -x["score"]), "ai"
    t = (topic or "").lower().split()
    pool = [x for x in DEMO_NICHES if not t or any(w in (x["name"] + x["pain_points"]).lower() for w in t)] or DEMO_NICHES
    return sorted((_finish_niche(x, "sample") for x in pool), key=lambda x: -x["score"])[:n], "sample"


# ---------------------------------------------------------------- resale insights
def rule_insights(rec, fin):
    p, m = rec["selling_price"], fin["margin_pct"]
    channels = (["Amazon (multipack/bundle)", "eBay", "TikTok Shop"] if p < 20 else
                ["Amazon", "Own Shopify store with social ads", "Walmart Marketplace"] if p <= 100 else
                ["Own Shopify store", "Amazon", "Niche forums and specialist retailers"])
    risks = []
    if m < 15: risks.append("Thin net margin leaves little room for returns or ad spend")
    if (rec.get("competition") or 0) >= 7: risks.append("Crowded market; expect price pressure")
    if rec.get("review_count") is not None and rec["review_count"] > 5000: risks.append("Incumbents hold thousands of reviews, making ranking hard")
    if (rec.get("demand") or 10) <= 4: risks.append("Weak demand signal")
    if rec.get("shipping_cost") and rec["shipping_cost"] / p > 0.15: risks.append("Shipping is a large share of price")
    if rec.get("data_label") != "user": risks.append("Figures are not verified; confirm with real supplier quotes and marketplace data")
    if m >= 30: strat = f"Margin supports competitive pricing. Test {p * 0.95:.2f}-{p:.2f} and keep room for promotions."
    elif m >= 15: strat = f"Hold the price near {p:.2f}; reduce costs or bundle to lift margin."
    else: strat = f"Break-even is {fin['break_even_price']:.2f}. Raise the price or negotiate sourcing below {fin['max_sourcing_cost']:.2f} for a {fin['target_margin_pct']:.0f}% margin."
    pot = "High" if rec.get("score", 0) >= 70 else "Moderate" if rec.get("score", 0) >= 50 else "Low"
    return {"resale_potential": pot, "channels": channels, "risks": risks or ["No major risks flagged from the supplied data"],
            "pricing_strategy": strat, "source": "rules"}


def ai_insights(records, model=None):
    """Optional AI narrative for up to 20 products. Returns {name: insight}."""
    slim = [{k: r.get(k) for k in ("name", "category", "selling_price", "sourcing_cost", "shipping_cost", "demand", "competition", "rating", "review_count", "score")} for r in records[:20]]
    prompt = f"""For each product give a resale analysis using ONLY the supplied data plus general knowledge.
Products: {json.dumps(slim)}
Return JSON {{"analyses":[{{"name","resale_potential"(High/Moderate/Low),"channels":[],"risks":[],"pricing_strategy","missing_info":[]}}]}}.
Do not invent URLs, suppliers or reviews."""
    out = {}
    for a in (call_json(prompt, model) or {}).get("analyses", []):
        try:
            out[a["name"]] = {"resale_potential": clean_text(a.get("resale_potential"), 20), "channels": [clean_text(x, 100) for x in a.get("channels", [])][:5],
                              "risks": [clean_text(x, 200) for x in a.get("risks", [])][:6], "pricing_strategy": clean_text(a.get("pricing_strategy"), 400),
                              "missing": [clean_text(x, 150) for x in a.get("missing_info", [])][:5], "source": "ai"}
        except (KeyError, AttributeError):
            continue
    return out
