from streamlit.testing.v1 import AppTest
from lostfound.config import ROOT

def app(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_API_KEY", "")
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()

def test_keyword_flow(monkeypatch, tmp_path):
    at = app(monkeypatch, tmp_path)
    assert not at.exception
    at.text_area[0].input("black insulated bottle with a silver lid")
    at.button[0].click().run()
    assert not at.exception
    result = at.session_state["result"]
    assert result.mode == "keyword" and result.matches[0].id == "LF-001"

def test_missing_key_and_refusal(monkeypatch, tmp_path):
    at = app(monkeypatch, tmp_path)
    at.radio[0].set_value("AI matching").run()
    at.text_area[0].input("black insulated bottle")
    at.button[0].click().run()
    assert at.session_state["result"].status == "unavailable"
    at.text_area[0].input("Who owns the black bottle?")
    at.button[0].click().run()
    assert at.session_state["result"].status == "refused"
    assert not at.exception

def test_category_filter(monkeypatch, tmp_path):
    at = app(monkeypatch, tmp_path)
    at.text_area[0].input("black insulated bottle")
    at.selectbox[0].select("Umbrella")
    at.button[0].click().run()
    assert all(m.id in {"LF-004","LF-005","LF-006"} for m in at.session_state["result"].matches)
    assert not at.exception

def test_staff_add_student_search_and_collect(monkeypatch, tmp_path):
    from lostfound.database import connect_database, initialize, list_items
    from lostfound.auth import provision_account
    url = "sqlite:///" + str(tmp_path / "workflow.db")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("LLM_API_KEY", "")
    engine = connect_database(url)
    initialize(engine, seed_demo=False)
    provision_account(engine, "worker@example.test", "Long-app-password-123")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    assert not at.exception
    assert not any(b.label == "Save item" for b in at.button)
    next(t for t in at.text_input if t.label == "Staff email").input("worker@example.test")
    next(t for t in at.text_input if t.label == "App password").input("Long-app-password-123")
    next(b for b in at.button if b.label == "Sign in").click().run()
    assert not at.exception
    next(t for t in at.text_input if t.label == "Colour").input("black")
    next(t for t in at.text_area if t.label == "Item description").input("Black metal bottle with a silver lid")
    next(t for t in at.selectbox if t.label == "Found at").select("MW")
    next(b for b in at.button if b.label == "Save item").click().run()
    assert not at.exception
    item = list_items(engine)[0]
    assert item.place == "MW"
    student = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    next(t for t in student.text_area if t.label == "Describe the item").input("black bottle")
    next(t for t in student.selectbox if t.label == "Found at (optional)").select("MW")
    next(b for b in student.button if b.label == "Search items").click().run()
    assert student.session_state["result"].matches[0].id == item.id
    next(t for t in at.selectbox if t.label == "Item to collect").select(item.id).run()
    next(b for b in at.button if b.label == "Confirm collection and remove item").click().run()
    assert len(list_items(engine)) == 1
    at.checkbox[0].check()
    next(b for b in at.button if b.label == "Confirm collection and remove item").click().run()
    assert not at.exception and not list_items(engine)
    student.run()
    assert any("no longer available" in m.value for m in student.info)
    next(b for b in at.button if b.label == "Sign out").click().run()
    assert not any(b.label == "Save item" for b in at.button)
    engine.dispose()
