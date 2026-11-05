import os, sys, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "a.db")
[os.environ.pop(k, None) for k in ("OPENAI_API_KEY", "GROQ_API_KEY")]
from streamlit.testing.v1 import AppTest

PAGES = ["📊 Overview", "🔍 Product Discovery", "⚖️ Product Comparison", "🧭 Niche Research", "🧮 Profit Calculator",
         "🔬 Resale Analyzer", "⭐ Saved Products", "📄 Reports & Exports", "⚙️ Settings"]


def test_all_pages_render_without_exceptions():
    at = AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py"), default_timeout=60).run()
    assert not at.exception
    for p in PAGES:
        at.sidebar.radio[0].set_value(p).run()
        assert not at.exception, (p, at.exception)


def test_workflows():
    at = AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py"), default_timeout=60).run()
    at.sidebar.radio[0].set_value("🔍 Product Discovery").run()
    at.button[0].click().run(); assert not at.exception and len(at.dataframe) >= 1
    at.sidebar.radio[0].set_value("🧭 Niche Research").run()
    at.button[0].click().run(); assert not at.exception and len(at.dataframe) >= 1
    at.sidebar.radio[0].set_value("⚖️ Product Comparison").run(); assert not at.exception
    assert any("Best fit" in str(t.value) for t in at.table)
    at.sidebar.radio[0].set_value("🧮 Profit Calculator").run()
    at.number_input[0].set_value(100.0).run(); assert not at.exception
    at.sidebar.radio[0].set_value("🔬 Resale Analyzer").run()
    [b for b in at.button if "sample dataset" in b.label][0].click().run(); assert not at.exception
    at.sidebar.radio[0].set_value("📊 Overview").run(); assert at.metric and not at.exception
