import datetime as dt, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from engine import KB, analyze, answer, build_markdown, build_docx

SAMPLES = pathlib.Path(__file__).resolve().parent.parent / "sample_docs"
TODAY = dt.date(2026, 11, 23)

def load(*names):
    kb = KB()
    for n in names: kb.add(n, (SAMPLES / n).read_bytes())
    kb.build(); return kb

def full():
    kb = load("project_proposal.txt", "meeting_notes.txt", "tasks.csv")
    return kb, analyze(kb, TODAY)

def test_ingestion_all_formats():
    kb, _ = full()
    assert len(kb.docs) == 3 and len(kb.tasks) == 6 and kb.chunks

def test_scope_agent():
    _, a = full()
    assert a["goals"] and a["dates"] and {"Priya", "Rahul"} <= set(a["owners"])

def test_risk_and_forecast():
    _, a = full()
    assert any(r["Category"] == "Schedule" for r in a["risks"])
    assert a["forecast"]["available"] and a["forecast"]["overdue"] >= 1 and a["forecast"]["status"] != "On track"

def test_blockers_actions():
    _, a = full()
    assert a["blockers"] and any(x["Owner"] == "Priya" for x in a["actions"])

def test_generated_docs():
    _, a = full()
    assert a["user_stories"][0]["acceptance"] and a["risk_register"][0]["ID"] == "R-1"
    assert "Risk register" in build_markdown(a) and build_docx(a)[:2] == b"PK"

def test_health_bounds():
    _, a = full()
    assert all(0 <= a["health"][k] <= 100 for k in ("scope", "timeline", "blockers", "overall"))

def test_assistant_grounded():
    kb, a = full()
    assert "risk" in answer(kb, a, "What are our biggest risks?").lower()
    assert "couldn't find" in answer(kb, a, "quantum banana jurisdiction").lower()

def test_incremental_upload_changes_results():
    kb1 = load("project_proposal.txt")
    kb2 = load("project_proposal.txt", "meeting_notes.txt")
    assert len(analyze(kb2, TODAY)["blockers"]) > len(analyze(kb1, TODAY)["blockers"])

def test_risk_level_method():
    from modules import risk_scoring as rs
    hi = rs.rate_text("The release is delayed and the demo deadline will be missed.", "Schedule")
    lo = rs.rate_text("A minor cosmetic bug was reported on the settings page.", "Technical")
    assert hi["Level"] == "High" and lo["Level"] == "Low" and hi["Score"] == hi["L"] * hi["I"]
    assert rs.rate_text("The crash has been fixed and verified.", "Technical") is None   # resolved -> not a risk
    assert rs.rate_text("The bug is not fixed.", "Technical") is not None                # negation handled

def test_task_risk_uses_priority_and_age():
    import datetime as dt
    from modules import risk_scoring as rs
    base = {"due": "2026-10-01", "priority": "High"}
    assert rs.rate_task(base, dt.date(2026, 11, 23))["Level"] == "High"
    assert rs.rate_task({"due": "2026-11-22", "priority": "Low"}, dt.date(2026, 11, 23))["Score"] < 15
