"""Transparent 0-100 opportunity score. All weights are visible in the UI."""
from .calc import calculate_profit
from .config import DEFAULT_FEE_PCT

W = {"Profit margin": 30, "Demand": 25, "Low competition": 20, "Return on investment": 15, "Data reliability": 10}
RELIABILITY = {"user": 10, "verified": 10, "sample": 5, "ai": 4}


def finance(rec):
    return calculate_profit(rec.get("sourcing_cost", 0), rec.get("selling_price", 0),
                            rec.get("shipping_cost") or 0,
                            DEFAULT_FEE_PCT if rec.get("fee_pct") is None else rec["fee_pct"],
                            advertising=rec.get("advertising_cost") or 0)


def opportunity_score(rec):
    fin = finance(rec)
    missing, rows = [], []

    def add(name, pts, note):
        rows.append({"Criterion": name, "Points": round(pts, 1), "Max": W[name], "Why": note})

    m = fin["margin_pct"]
    add("Profit margin", max(0, min(m / 40, 1)) * W["Profit margin"], f"Net margin {m:.1f}% (40%+ earns full points)")
    d = rec.get("demand")
    if d is None:
        missing.append("Demand indicator (neutral 5/10 assumed)")
    d_eff = 5 if d is None else d
    add("Demand", d_eff / 10 * W["Demand"], f"Demand {d_eff}/10" + (" (assumed)" if d is None else ""))
    c = rec.get("competition")
    if c is None:
        missing.append("Competition level (neutral 5/10 assumed)")
    c_eff = 5 if c is None else c
    add("Low competition", (10 - c_eff) / 10 * W["Low competition"], f"Competition {c_eff}/10" + (" (assumed)" if c is None else ""))
    add("Return on investment", max(0, min(fin["roi_pct"] / 100, 1)) * W["Return on investment"], f"ROI {fin['roi_pct']:.0f}% (100%+ earns full points)")
    lab = rec.get("data_label", "user")
    add("Data reliability", RELIABILITY.get(lab, 5), {"user": "User-entered data", "sample": "Illustrative sample data",
                                                       "ai": "AI estimate, not verified", "verified": "Verified data"}.get(lab, lab))
    for k, nm in (("rating", "Customer rating"), ("review_count", "Review count"), ("shipping_cost", "Shipping cost")):
        if rec.get(k) is None:
            missing.append(nm)
    return {"score": round(sum(r["Points"] for r in rows)), "breakdown": rows, "missing": missing, **fin}


def pros_cons(rec, fin):
    pros, cons = list(rec.get("pros") or []), list(rec.get("cons") or [])
    if not pros and not cons:
        m = fin["margin_pct"]
        (pros if m >= 25 else cons).append(f"Net margin {m:.0f}% " + ("is healthy" if m >= 25 else "is thin"))
        if (rec.get("demand") or 5) >= 7: pros.append("Strong demand signal")
        if (rec.get("demand") or 5) <= 4: cons.append("Weak demand signal")
        if (rec.get("competition") or 5) <= 4: pros.append("Low competition")
        if (rec.get("competition") or 5) >= 7: cons.append("Crowded market")
        if fin["roi_pct"] >= 80: pros.append(f"ROI {fin['roi_pct']:.0f}%")
    return pros, cons


def niche_score(n):
    parts = [("Demand", n["demand"] / 10 * 20, 20, f"Demand {n['demand']}/10"),
             ("Growth potential", n["growth"] / 10 * 15, 15, f"Growth {n['growth']}/10"),
             ("Low competition", (10 - n["competition"]) / 10 * 15, 15, f"Competition {n['competition']}/10"),
             ("Differentiation", n["differentiation"] / 10 * 10, 10, f"Differentiation room {n['differentiation']}/10"),
             ("Profit potential", max(0, min(n["margin_pct"] / 45, 1)) * 20, 20, f"Typical margin ~{n['margin_pct']:.0f}%"),
             ("Seasonal stability", n["seasonality"] / 10 * 10, 10, f"Stability {n['seasonality']}/10 (10 = year-round)"),
             ("Ease of entry", (10 - n["entry_barrier"]) / 10 * 10, 10, f"Entry barriers {n['entry_barrier']}/10")]
    bd = [{"Criterion": a, "Points": round(b, 1), "Max": c, "Why": d} for a, b, c, d in parts]
    return round(sum(r["Points"] for r in bd)), bd
