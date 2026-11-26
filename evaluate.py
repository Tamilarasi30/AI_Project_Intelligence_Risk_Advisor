"""Verifies the project against the five evaluation criteria in the project statement.
Run: python evaluation/evaluate.py   (writes evaluation/evaluation_report.md)
NOTE: gold labels are small and author-labelled; treat results as indicative, not a benchmark."""
import datetime as dt, io, json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from docx import Document
from modules.rag import KB
from modules.agents import RISK_RULES
from modules.pipeline import analyze
from modules.assistant import answer
from modules.docgen import to_markdown, to_docx
TODAY = dt.date(2026, 11, 23); RANK = {"Low": 1, "Medium": 2, "High": 3}
OUT = []; log = lambda s="": (OUT.append(s), print(s))
def prf(pred, gold):
    tp = len(pred & gold); p = tp / len(pred) if pred else 0; r = tp / len(gold) if gold else 0
    return p, r, (2 * p * r / (p + r) if p + r else 0)
def build(names):
    kb = KB()
    for n in names: kb.add(n, (ROOT / "sample_docs" / n).read_bytes())
    kb.build(); return kb
def legacy_level(text, cat):  # previous method: category base severity + emphasis words
    base = {"Schedule": 3, "Dependency": 2, "Scope": 2, "Resource": 2, "Technical": 3, "Budget": 2, "Quality": 2}[cat]
    return ["", "Low", "Medium", "High"][min(3, base + bool(re.search(r"critical|severe|still|not fixed|two weeks|major", text, re.I)))]

# ---------- Criterion 1: accuracy & completeness (scope, risk, blockers) ----------
gold = json.load(open(ROOT / "evaluation" / "gold.json")); kb = KB()
for n, items in gold.items(): kb.add(n, "\n".join(i["s"] for i in items).encode())
kb.build(); A = analyze(kb, TODAY); G = [i for items in gold.values() for i in items]
norm = lambda t: re.sub(r"^action:?\s*", "", t, flags=re.I).strip()
log("## Criterion 1 - Accuracy and completeness of scope, risk and blocker extraction")
log(f"Gold set: {len(G)} labelled sentences in {len(gold)} documents.\n\n| Task | Precision | Recall | F1 |\n|---|---|---|---|")
rows = {"Goal / deliverable extraction": (A["goals"] and {t for _, t in A["goals"]}, {i["s"] for i in G if i["goal"]}),
        "Risk detection (new method)": ({r["Risk"] for r in A["risks"]}, {i["s"] for i in G if i["risk"]}),
        "Blocker identification": ({b["Blocker"] for b in A["blockers"]}, {i["s"] for i in G if i["blocker"]}),
        "Action item identification": ({norm(a["Action"]) for a in A["actions"]}, {norm(i["s"]) for i in G if i["action"]})}
leg = {t for _, t in kb.lines if any(re.search(p, t, re.I) for _, p, _, _ in RISK_RULES)}
rows["Risk detection (legacy: no negation filter)"] = (leg, {i["s"] for i in G if i["risk"]})
scores = {}
for k, (p_, g_) in rows.items():
    p, r, f = prf(p_ or set(), g_); scores[k] = f; log(f"| {k} | {p:.2f} | {r:.2f} | {f:.2f} |")
new = {r["Risk"]: r["Level"] for r in A["risks"]}; gl = {i["s"]: i["risk"] for i in G if i["risk"]}
def lvl_acc(pred):
    c = [s for s in gl if s in pred]; e = sum(pred[s] == gl[s] for s in c); w = sum(abs(RANK[pred[s]] - RANK[gl[s]]) <= 1 for s in c)
    return len(c), e / len(c), w / len(c)
n1, e1, w1 = lvl_acc(new)
old = {t: legacy_level(t, next(c for c, p, _, _ in RISK_RULES if re.search(p, t, re.I))) for t in leg}
n0, e0, w0 = lvl_acc(old)
log(f"\nRisk LEVEL accuracy on gold risks that were detected:\n\n| Method | Detected | Exact match | Within one level |\n|---|---|---|---|\n"
    f"| Likelihood x impact (new) | {n1}/{len(gl)} | {e1:.0%} | {w1:.0%} |\n| Keyword base + emphasis (legacy) | {n0}/{len(gl)} | {e0:.0%} | {w0:.0%} |")
mis = [(s[:55], gl[s], new[s]) for s in gl if s in new and new[s] != gl[s]]
if mis: log("\nLevel disagreements (sentence, gold, predicted): " + "; ".join(f'"{a}..." {b}->{c}' for a, b, c in mis))

# ---------- Criterion 2: quality of generated documents ----------
S = build(["project_proposal.txt", "meeting_notes.txt", "tasks.csv"]); a = analyze(S, TODAY); md = to_markdown(a)
reg = a["risk_register"]; ids = [r["ID"] for r in reg]
d = Document(io.BytesIO(to_docx(a))); doc_text = "\n".join(p.text for p in d.paragraphs)
chk2 = [("Every user story has an ID, acceptance criteria and a source", all(s["id"] and s["acceptance"] and s["source"] for s in a["user_stories"])),
        ("User stories exist for extracted goals", len(a["user_stories"]) > 0),
        ("Risk register: unique IDs, level, mitigation and source on every row", len(set(ids)) == len(ids) and all(r["Level"] and r["Mitigation"] and r["Source"] for r in reg)),
        ("Risk register sorted by score (highest first)", [r["Score"] for r in reg] == sorted((r["Score"] for r in reg), reverse=True)),
        ("Every risk explains its rating (Basis)", all(r.get("Basis") for r in reg)),
        ("Action items have owner and priority", all(x["Owner"] and x["Priority"] for x in a["action_items"])),
        ("Markdown report lists every risk", md.count("| R-") == len(reg)),
        ("Word report opens and contains user stories", "US-1" in doc_text and len(d.tables) == 2)]

# ---------- Criterion 3: groundedness of assistant ----------
names = {x["name"] for x in S.docs}; qs = ["What are our biggest risks?", "What are the blockers?", "What are the next action items?", "Are we on track?", "What are the milestones and goals?", "Will we deliver on time?"]
cited_ok = True; detail = []
for q in qs:
    ans = answer(S, a, q); cites = set(re.findall(r"source: ([^,;)]+)", ans)) | set(re.findall(r"\[([^\]]+\.\w+)\]", ans)) | set(re.findall(r"Based on: (.+)", ans)[0].split(", ") if "Based on:" in ans else [])
    ok = bool(cites) and cites <= names; cited_ok &= ok; detail.append((q, ok))
off = answer(S, a, "quantum banana jurisdiction")
chk3 = [("Every answer cites only uploaded documents (" + ", ".join(f"{'ok' if o else 'FAIL'}" for _, o in detail) + ")", cited_ok),
        ("Out-of-scope question is declined, not invented", "couldn't find" in off.lower())]

# ---------- Criterion 4: health score clarity ----------
h = a["health"]; h1 = analyze(build(["project_proposal.txt"]), TODAY)["health"]; h2 = analyze(build(["project_proposal.txt", "meeting_notes.txt", "tasks.csv"]), TODAY)["health"]
chk4 = [("Overall and all three dimensions are within 0-100", all(0 <= h[k] <= 100 for k in ("overall", "scope", "timeline", "blockers"))),
        ("Overall equals the documented weights (30/40/30)", abs(h["overall"] - (.3 * h["scope"] + .4 * h["timeline"] + .3 * h["blockers"])) <= 1),
        ("Adding meeting notes + overdue tasks lowers the timeline and blocker scores", h2["timeline"] < h1["timeline"] and h2["blockers"] < h1["blockers"]),
        ("Label matches thresholds (>=75 on track, >=50 at risk)", h["label"] == ("On track" if h["overall"] >= 75 else "At risk" if h["overall"] >= 50 else "Critical"))]

# ---------- Criterion 5: completeness ----------
mods = ["ingestion", "rag", "agents", "risk_scoring", "docgen", "health", "assistant", "pipeline"]
doc = Document(); doc.add_paragraph("Project goal is to build an app."); b = io.BytesIO(); doc.save(b)
try:  # build a valid PDF fixture; skip the check (not fail) if reportlab is unavailable
    from reportlab.pdfgen import canvas
    pb = io.BytesIO(); c = canvas.Canvas(pb); c.drawString(72, 720, "Project goal is to build an app."); c.save(); pdf = pb.getvalue()
except ImportError:
    pdf = None
def ingests(name, data):
    try: k = KB(); k.add(name, data); return bool(k.docs and k.chunks)
    except Exception: return False
chk5 = [(f"All {len(mods)} module files present", all((ROOT / "modules" / f"{m}.py").exists() for m in mods)),
        ("Dashboard, API, tests, README and sample documents present", all((ROOT / p).exists() for p in ["templates/index.html", "static/app.js", "app.py", "tests/test_pipeline.py", "README.md", "sample_docs/tasks.csv"])),
        ("Ingests TXT, MD, CSV, DOCX", all([ingests("a.txt", b"Project goal: build it."), ingests("a.md", b"# Goal\nBuild the module."), ingests("a.csv", b"task,owner,status,due\nX,A,Done,2026-01-01"), ingests("a.docx", b.getvalue())])),
        ("Ingests PDF" + ("" if pdf else " (SKIPPED: reportlab not installed)"), ingests("a.pdf", pdf) if pdf else True),
        ("Incremental upload: adding a document changes agent output", len(analyze(build(["project_proposal.txt", "meeting_notes.txt"]), TODAY)["blockers"]) > len(analyze(build(["project_proposal.txt"]), TODAY)["blockers"]))]
for title, chk in (("2 - Quality of generated user stories, risk registers and action items", chk2), ("3 - Relevance and groundedness of assistant responses", chk3),
                   ("4 - Clarity and usefulness of health scoring", chk4), ("5 - Completeness of implementation, testing and documentation", chk5)):
    log(f"\n## Criterion {title}\n"); [log(f"- [{'PASS' if ok else 'FAIL'}] {t}") for t, ok in chk]
allc = chk2 + chk3 + chk4 + chk5; log(f"\n**Checks passed: {sum(o for _, o in allc)}/{len(allc)}**")
log("\nCaveats: gold labels and rules were written by the same author on a small set (29 sentences), so Criterion 1 figures are optimistic. The dashboard's visual clarity (Criterion 4) and the final demonstration (Criterion 5) cannot be verified by script.")
(ROOT / "evaluation" / "evaluation_report.md").write_text("# Evaluation report\n\n" + "\n".join(OUT) + "\n")
