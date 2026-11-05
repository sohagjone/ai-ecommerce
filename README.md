# 🛒 AI E-commerce Product Finder

A Streamlit app for sellers, dropshippers and resellers: discover products, compare them, rank niches, calculate resale profit, analyse CSV/Excel product lists and export PDF / Excel / CSV reports.

**Works without an API key** in clearly labelled *demo mode* (built-in illustrative sample data). Add a Groq API key for AI mode.

## Honesty about data
- No scraping and no live marketplace data. Prices, demand and competition are **user-entered**, **sample** or **AI estimates**, and every result is labelled with its source.
- The AI prompt forbids invented URLs, suppliers, reviews and live prices. The score only *uses* AI numbers; it is computed by transparent code (see below).
- Nothing here guarantees profit or demand.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional: add OPENAI_API_KEY
streamlit run app.py
```

## Configure AI (optional, Groq)
Get a key at https://console.groq.com/keys, then set it in `.env` (local) or Streamlit **Secrets** (cloud):
```
GROQ_API_KEY="gsk_..."
GROQ_MODEL="openai/gpt-oss-120b"   # optional; Settings can list the models your key can use
```
Groq's OpenAI-compatible endpoint is used (`https://api.groq.com/openai/v1`). `OPENAI_API_KEY` / `OPENAI_MODEL` still work as an optional fallback when no Groq key is set. Keys are read from env/secrets only, never shown in the UI or exports. Rate limits and API errors are retried/handled with friendly messages. Optional marketplace data APIs are not bundled; add your own authorised source and label it `verified`.

## Pages
Overview · Product Discovery · Product Comparison (2-5 products) · Niche Research · Profit Calculator · Resale Analyzer (manual / CSV / Excel / sample) · Saved Products · Reports & Exports · Settings.

## Scoring (all weights shown in the app)
- **Product score (0-100):** net margin 30 · demand 25 · low competition 20 · ROI 15 · data reliability 10 (user/verified 10, sample 5, AI estimate 4). Missing demand/competition default to a neutral 5/10 and are flagged.
- **Niche score (0-100):** demand 20 · growth 15 · low competition 15 · differentiation 10 · profit potential 20 · seasonal stability 10 · ease of entry 10.
- **Profit:** fees = price × fee% + fixed fee; net = price − sourcing − shipping − packaging − fees − ads − other; margin = net/price; ROI = net/total cost; break-even = (fixed costs) / (1 − fee%); max sourcing = price·(1 − target margin − fee%) − other costs. Gross profit = price − sourcing − shipping − packaging.

## Import format
Required columns: `name`, `selling_price`, `sourcing_cost`. Optional: `category, shipping_cost, fee_pct, demand, competition (1-10 or low/medium/high), rating, review_count, features, target_customer, description`. Common aliases (`price`, `cost`, `product`…) are recognised. Invalid rows are skipped and listed with row numbers. Limits: 5 MB, 500 rows. Spreadsheet-formula injection in exports is neutralised.

## Deploy to Streamlit Community Cloud
1. Push this folder to a GitHub repo (`.env` and `data/app.db` are git-ignored).
2. On share.streamlit.io choose **New app**, select the repo, main file `app.py`.
3. *Advanced settings → Secrets*: paste `GROQ_API_KEY = "gsk_..."` (optional).
4. Deploy. Note: SQLite storage on Community Cloud is **ephemeral** (reset on restart); download reports you need, or point `DB_PATH` at persistent storage elsewhere.

## Tests
```bash
pip install pytest && python -m pytest -q tests
```
Covers known profit examples, CSV/Excel validation, demo discovery, DB, PDF/Excel/CSV export, and an end-to-end run of every page.

## Layout
`app.py` entry · `features/` one module per page · `core/` calc, scoring, db, data, ai, reports, ui · `data/sample_products.csv` · `sample_report/` example exports.

## Commercial use
Review Groq's terms and your marketplaces' policies; add authentication and a persistent database before offering this as multi-user SaaS.
