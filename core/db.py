"""SQLite persistence (local file). Stores only product/niche research, no personal data."""
import contextlib, json, os, sqlite3
from datetime import datetime

from .config import DB_PATH
from .scoring import opportunity_score

SCHEMA = """
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT,
  source TEXT, score REAL, margin REAL, saved INTEGER DEFAULT 0, data TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS niches(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, score REAL, data TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
"""


@contextlib.contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def add_products(records, saved=False):
    """Score and store records. Returns the records with id/score/margin attached."""
    out = []
    with conn() as c:
        for r in records:
            s = opportunity_score(r)
            r = {**r, "score": s["score"], "margin": s["margin_pct"], "roi": s["roi_pct"],
                 "net_profit": s["net_profit"], "breakdown": s["breakdown"], "missing": s["missing"]}
            cur = c.execute("INSERT INTO products(name,category,source,score,margin,saved,data,created_at) VALUES(?,?,?,?,?,?,?,?)",
                            (r["name"], r.get("category"), r.get("data_label"), r["score"], r["margin"], int(saved),
                             json.dumps(r), _now()))
            out.append({**r, "id": cur.lastrowid, "saved": int(saved)})
    return out


def list_products(saved_only=False, limit=None):
    q = "SELECT * FROM products" + (" WHERE saved=1" if saved_only else "") + " ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    with conn() as c:
        rows = c.execute(q).fetchall()
    return [{**json.loads(r["data"]), "id": r["id"], "saved": r["saved"], "created_at": r["created_at"]} for r in rows]


def set_saved(pid, flag=True):
    with conn() as c:
        c.execute("UPDATE products SET saved=? WHERE id=?", (int(flag), int(pid)))


def delete_product(pid):
    with conn() as c:
        c.execute("DELETE FROM products WHERE id=?", (int(pid),))


def add_niches(niches):
    with conn() as c:
        for n in niches:
            c.execute("INSERT INTO niches(name,score,data,created_at) VALUES(?,?,?,?)",
                      (n["name"], n["score"], json.dumps(n), _now()))


def list_niches(limit=None):
    q = "SELECT * FROM niches ORDER BY id DESC" + (f" LIMIT {int(limit)}" if limit else "")
    with conn() as c:
        return [json.loads(r["data"]) for r in c.execute(q).fetchall()]


def get_setting(key, default=None):
    with conn() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(key, value):
    with conn() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def stats():
    with conn() as c:
        n = c.execute("SELECT COUNT(*) n, AVG(margin) m FROM products").fetchone()
        sv = c.execute("SELECT COUNT(*) FROM products WHERE saved=1").fetchone()[0]
        nn = c.execute("SELECT COUNT(*) FROM niches").fetchone()[0]
    return {"products": n["n"], "avg_margin": n["m"], "saved": sv, "niches": nn}


def clear_all():
    with conn() as c:
        c.executescript("DELETE FROM products; DELETE FROM niches;")
