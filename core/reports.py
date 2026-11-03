"""PDF / Excel / CSV report builders."""
import io
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from .data import safe_cell
from .scoring import finance, pros_cons

LABELS = {"ai": "AI estimate", "sample": "Sample data", "user": "User-entered", "verified": "Verified"}
DISCLAIMER = ("Figures labelled 'AI estimate' or 'Sample data' are assumptions, not verified market data. "
              "Nothing in this report guarantees profit or future demand.")


def products_df(recs):
    rows = []
    for r in recs:
        f = finance(r)
        rows.append({"Product": r["name"], "Category": r.get("category"), "Selling price": r["selling_price"], "Sourcing cost": r["sourcing_cost"],
                     "Shipping": r.get("shipping_cost") or 0, "Fees": round(f["fees"], 2), "Net profit": round(f["net_profit"], 2),
                     "Margin %": round(f["margin_pct"], 1), "ROI %": round(f["roi_pct"], 1), "Demand /10": r.get("demand"), "Competition /10": r.get("competition"),
                     "Rating": r.get("rating"), "Reviews": r.get("review_count"), "Score": r.get("score"), "Data source": LABELS.get(r.get("data_label"), r.get("data_label"))})
    return pd.DataFrame(rows)


def niches_df(ns):
    return pd.DataFrame([{"Niche": n["name"], "Score": n["score"], "Demand": n["demand"], "Growth": n["growth"], "Competition": n["competition"],
                          "Avg price": n["avg_price"], "Margin %": n["margin_pct"], "Seasonal stability": n["seasonality"], "Entry barrier": n["entry_barrier"],
                          "Pain points": n.get("pain_points"), "Data source": LABELS.get(n.get("data_label"), n.get("data_label"))} for n in ns])


def calc_df(calc):
    if not calc: return pd.DataFrame()
    i, o = calc["inputs"], calc["result"]
    return pd.DataFrame([("Selling price", i["price"]), ("Sourcing cost", i["sourcing"]), ("Shipping", i["shipping"]), ("Marketplace fee %", i["fee_pct"]),
                         ("Fixed fee", i["fixed_fee"]), ("Packaging", i["packaging"]), ("Advertising", i["advertising"]), ("Other", i["other"]),
                         ("Total cost", o["total_cost"]), ("Gross profit", o["gross_profit"]), ("Net profit", o["net_profit"]), ("Margin %", o["margin_pct"]),
                         ("ROI %", o["roi_pct"]), ("Break-even price", o["break_even_price"]), (f"Max sourcing for {o['target_margin_pct']:.0f}% margin", o["max_sourcing_cost"])],
                        columns=["Item", "Value"]).round(2)


def summary_text(recs, niches):
    if not recs:
        return "No products were included in this report."
    best = max(recs, key=lambda r: r.get("score", 0))
    avg = sum(finance(r)["margin_pct"] for r in recs) / len(recs)
    t = f"This report covers {len(recs)} product(s) with an average estimated net margin of {avg:.1f}%. The highest-scoring opportunity is '{best['name']}' (score {best.get('score', 0)}/100)."
    if niches:
        t += f" {len(niches)} niche(s) were analysed; the top niche is '{max(niches, key=lambda n: n['score'])['name']}'."
    return t


def risks_text(recs):
    out = []
    for r in recs:
        out += [f"{r['name']}: {x}" for x in r.get("insight", {}).get("risks", [])] if r.get("insight") else []
        f = finance(r)
        if f["margin_pct"] < 15: out.append(f"{r['name']}: thin margin ({f['margin_pct']:.0f}%)")
        if (r.get("competition") or 0) >= 8: out.append(f"{r['name']}: very high competition")
        if r.get("missing"): out.append(f"{r['name']}: missing data - {', '.join(r['missing'])}")
    return list(dict.fromkeys(out))[:25] or ["No major risks flagged from the supplied data."]


def assumptions(recs, niches):
    srcs = sorted({LABELS.get(r.get("data_label"), "?") for r in recs} | {LABELS.get(n.get("data_label"), "?") for n in niches})
    return [f"Data sources used: {', '.join(srcs) or 'none'}.", "Net profit = price - sourcing - shipping - marketplace fees - advertising. Default marketplace fee 12% when not supplied.",
            "Opportunity score = margin (30) + demand (25) + low competition (20) + ROI (15) + data reliability (10).", DISCLAIMER]


def build_csv(recs):
    df = products_df(recs).map(safe_cell)
    return df.to_csv(index=False).encode("utf-8")


def build_excel(title, recs, niches, calc):
    buf = io.BytesIO()
    summary = pd.DataFrame({"Report": [title, datetime.now().strftime("%Y-%m-%d %H:%M"), summary_text(recs, niches), DISCLAIMER]}, index=["Title", "Generated", "Executive summary", "Disclaimer"])
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        summary.map(safe_cell).to_excel(xw, sheet_name="Summary")
        pdf = products_df(recs).map(safe_cell)
        pdf.to_excel(xw, sheet_name="Products", index=False)
        pdf.sort_values("Score", ascending=False).to_excel(xw, sheet_name="Rankings", index=False)
        if niches: niches_df(niches).map(safe_cell).to_excel(xw, sheet_name="Niches", index=False)
        if calc: calc_df(calc).to_excel(xw, sheet_name="Profit calculation", index=False)
        pd.DataFrame({"Risks": risks_text(recs)}).map(safe_cell).to_excel(xw, sheet_name="Risks", index=False)
        pd.DataFrame({"Data sources & assumptions": assumptions(recs, niches)}).to_excel(xw, sheet_name="Assumptions", index=False)
        for ws in xw.book.worksheets:
            from openpyxl.styles import Font, PatternFill
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF", name="Arial"); c.fill = PatternFill("solid", fgColor="1F3A5F")
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(60, max(12, max(len(str(c.value or "")) for c in col) + 2))
            ws.freeze_panes = "A2"
    return buf.getvalue()


def build_pdf(title, recs, niches, calc):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm, title=title)
    ss = getSampleStyleSheet()
    h1, h2, body = ss["Title"], ss["Heading2"], ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12)
    cell = ParagraphStyle("c", parent=body, fontSize=7.5, leading=9)
    head = ParagraphStyle("h", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    P = lambda t, s=body: Paragraph(escape(str(t)), s)

    def table(df, widths=None):
        data = [[P(c, head) for c in df.columns]] + [[P("" if pd.isna(v) else v, cell) for v in row] for row in df.itertuples(index=False)]
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                               ("ROWBACKGROUNDS", (1, 0), (-1, -1), [colors.white, colors.HexColor("#F3F6FA")]), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return t

    el = [P(title, h1), P(f"Generated {datetime.now():%Y-%m-%d %H:%M}", body), Spacer(1, 8), P("Executive summary", h2), P(summary_text(recs, niches))]
    if recs:
        d = products_df(recs)
        el += [P("Product comparison", h2), table(d[["Product", "Selling price", "Sourcing cost", "Fees", "Net profit", "Margin %", "Competition /10", "Data source"]])]
        el += [P("Opportunity rankings", h2), table(d.sort_values("Score", ascending=False)[["Product", "Score", "Margin %", "ROI %", "Demand /10"]])]
        el += [P("Pros and cons", h2)]
        for r in recs[:10]:
            pr, co = pros_cons(r, finance(r))
            el.append(P(f"{r['name']} - Pros: {'; '.join(pr) or 'n/a'}. Cons: {'; '.join(co) or 'n/a'}."))
    if niches:
        el += [P("Niche analysis", h2), table(niches_df(niches)[["Niche", "Score", "Demand", "Competition", "Margin %", "Data source"]])]
    if calc:
        el += [P("Profit calculation", h2), table(calc_df(calc))]
    el += [P("Risks and recommendations", h2)] + [P("- " + r) for r in risks_text(recs)]
    el += [P("Data sources and assumptions", h2)] + [P("- " + a) for a in assumptions(recs, niches)]
    doc.build(el)
    return buf.getvalue()
