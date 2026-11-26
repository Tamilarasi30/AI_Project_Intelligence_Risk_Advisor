"""Module 6 - Documentation generation: user stories, risk register, action items; Markdown and Word export."""
import datetime as dt, io, re
from docx import Document
from .ingestion import _parse_date

LEVEL = {"Low": 1, "Medium": 2, "High": 3}

def user_stories(goals):
    out = []
    for i, (src, goal) in enumerate(goals[:10], 1):
        clean = re.sub(r"^(project goal|deliverables?|scope[^:]*):\s*", "", goal, flags=re.I).rstrip(".")
        if re.match(r"as an? ", clean, re.I):
            story = clean
        else:
            clean = re.sub(r"^(the system (must|shall|should)|we (must|will|need to))\s+", "", clean, flags=re.I)
            story = f"As a project stakeholder, I want {clean[:1].lower() + clean[1:]}, so that the agreed project outcome is delivered."
        out.append({"id": f"US-{i}", "story": story, "source": src,
                    "acceptance": ["Feature is demonstrated to the team", "Related tasks are marked done", "Documentation is updated"]})
    return out

def risk_register(risks):
    reg = [{**r, "ID": "", "Score": r.get("Score") or LEVEL.get(r["Level"], 1) * LEVEL.get(r["Impact"], 1)} for r in risks]
    reg.sort(key=lambda r: -r["Score"])
    for i, r in enumerate(reg, 1):
        r["ID"] = f"R-{i}"
    return reg

def action_items(actions, today=None):
    today = today or dt.date.today()
    out = []
    for a in actions:
        d = _parse_date(a["Due"])
        out.append({**a, "Priority": "High" if d and (d - today).days <= 7 else "Normal"})
    return sorted(out, key=lambda a: a["Priority"] != "High")

def to_markdown(a):
    h, f = a["health"], a.get("forecast", {})
    r = ["# AI Project Intelligence & Risk Advisor Report", "",
         "> Generated from uploaded project files. Scores are heuristic indicators, not certified predictions.", "",
         "## Project health", f'- **Overall:** {h["overall"]}/100 ({h["label"]})', f'- **Scope clarity:** {h["scope"]}/100',
         f'- **Timeline safety:** {h["timeline"]}/100', f'- **Blocker score:** {h["blockers"]}/100', "",
         "## Delivery forecast", f.get("summary", "n/a"), "", "## Goals and deliverables"]
    r += [f"- {t} (source: {n})" for n, t in a["goals"]] + ["", "## Milestones and dates"]
    r += [f"- {t} (source: {n})" for n, t in a["dates"]] + ["", "## Team responsibilities"] + [f"- {o}" for o in a["owners"]]
    r += ["", "## User stories"]
    for s in a["user_stories"]:
        r += [f'- **{s["id"]}** {s["story"]}'] + [f"  - Acceptance: {c}" for c in s["acceptance"]]
    r += ["", "## Risk register", "| ID | Risk | Category | Level | Mitigation | Source |", "|---|---|---|---|---|---|"]
    for x in a["risk_register"]:
        r.append("| " + " | ".join(str(x[k]).replace("|", "/").replace("\n", " ") for k in ("ID", "Risk", "Category", "Level", "Mitigation", "Source")) + " |")
    r += ["", "## Blockers"] + [f'- {b["Blocker"]} (source: {b["Source"]})' for b in a["blockers"]]
    r += ["", "## Action items"] + [f'- [{x["Priority"]}] {x["Action"]} - Owner: {x["Owner"]}; Due: {x["Due"] or "Not specified"}; Source: {x["Source"]}' for x in a["action_items"]]
    return "\n".join(r) + "\n"

def to_docx(a):
    d, h, f = Document(), a["health"], a.get("forecast", {})
    d.add_heading("Project Intelligence & Risk Report", 0)
    d.add_paragraph(f'Overall health: {h["overall"]}/100 ({h["label"]}) | Scope {h["scope"]} | Timeline {h["timeline"]} | Blockers {h["blockers"]}')
    d.add_heading("Delivery forecast", 1); d.add_paragraph(f.get("summary", "n/a"))
    for title, items in (("Goals and deliverables", [f"{t} ({n})" for n, t in a["goals"]]),
                         ("Milestones", [f"{t} ({n})" for n, t in a["dates"]]), ("Team", a["owners"]),
                         ("Blockers", [b["Blocker"] for b in a["blockers"]])):
        d.add_heading(title, 1)
        for i in items: d.add_paragraph(i, style="List Bullet")
    d.add_heading("User stories", 1)
    for s in a["user_stories"]:
        d.add_paragraph(f'{s["id"]}: {s["story"]}', style="List Bullet")
    for title, cols, rows in (("Risk register", ("ID", "Risk", "Category", "Level", "Mitigation"), a["risk_register"]),
                              ("Action items", ("Action", "Owner", "Due", "Priority"), a["action_items"])):
        d.add_heading(title, 1)
        t = d.add_table(rows=1, cols=len(cols)); t.style = "Table Grid"
        for c, name in zip(t.rows[0].cells, cols): c.text = name
        for row in rows:
            for c, name in zip(t.add_row().cells, cols): c.text = str(row.get(name, ""))
    buf = io.BytesIO(); d.save(buf); return buf.getvalue()
