"""Modules 3-5 - Scope, Risk + Delivery Forecasting, and Blocker/Action agents."""
from __future__ import annotations
import datetime as dt, re
from . import risk_scoring as rs
from .ingestion import _parse_date, is_done

RISK_RULES = [
    ("Schedule", r"\bdelay(?:ed)?\b|\blate\b|\bbehind\b|\bslip\b|\boverdue\b|\bpostpone\b|\bmissed deadline\b", 3,
     "Re-plan the timeline, add a realistic buffer, and agree on a revised baseline."),
    ("Dependency", r"waiting on|\bdepend(?:ency|encies)?\b|third-party|\bvendor\b|\bapproval\b|\bblocked\b", 2,
     "Escalate the dependency, assign an owner, and prepare a fallback."),
    ("Scope", r"\btbd\b|\bunclear\b|\bundefined\b|\bnot sure\b|\bambiguous\b", 2,
     "Run a scope review and define measurable acceptance criteria."),
    ("Resource", r"\bsick\b|\bunavailable\b|\bresign(?:ed)?\b|\bon leave\b|\bshortage\b|\boverloaded\b", 2,
     "Assign a backup and rebalance workload."),
    ("Technical", r"\bbug\b|\bcrash\b|\bsecurity\b|\bfail(?:ure|ed)?\b|\bvulnerab", 3,
     "Prioritise remediation and add regression/security tests."),
    ("Quality", r"\bmissing documentation\b|documentation .{0,20}missing|\buntested\b|not (?:yet )?tested|\bno tests?\b|\bno testing\b", 2,
     "Add test and documentation tasks to the definition of done."),
    ("Budget", r"\bbudget\b|\bcost overrun\b|\bexpensive\b", 2,
     "Review actual spend against the approved budget and revise priorities."),
]


class ScopeAgent:
    """Extract goals, milestones, and team ownership from project evidence."""
    def run(self, kb):
        lines = kb.text_lines
        goals = [(name, text) for name, text in lines
                 if re.search(r"\bgoal\b|\bobjective\b|deliverable|scope|build|feature|module", text, re.I)
                 and not re.search(r"\btbd\b|unclear", text, re.I)]
        dates = [(name, text) for name, text in lines
                 if re.search(r"\b20\d{2}-\d{2}-\d{2}\b|milestone|week \d+", text, re.I)
                 and not name.lower().endswith(".csv")]
        ignored = {"Action", "Decision", "Milestone", "Blocker", "Sprint"}
        owners = {m for _, text in lines
                  for m in re.findall(r"\b([A-Z][a-z]+)\s+(?:is responsible|will|to)\b", text)} - ignored
        owners.update(t["owner"] for t in kb.tasks if t["owner"] != "Unassigned")
        return {"goals": goals, "dates": dates, "owners": sorted(owners)}

class RiskAgent:
    """Detect risk evidence, then level it with the likelihood x impact method in risk_scoring.py."""
    def run(self, kb, today=None):
        today = today or dt.date.today()
        cands = []
        for filename, text in kb.text_lines:
            for category, pattern, _base, mitigation in RISK_RULES:
                if re.search(pattern, text, re.I):
                    cands.append((filename, text, category, mitigation)); break
        risks, seen = [], set()
        for filename, text, category, mitigation in cands:
            if text in seen:
                continue
            seen.add(text)
            rating = rs.rate_text(text, category, rs.corroboration(text, category, filename, cands))
            if rating:  # None = resolved/negated statement, not a live risk
                risks.append({"Risk": text, "Category": category, "Mitigation": mitigation, "Source": filename, **rating})
        for t in kb.tasks:
            overdue = (d := _parse_date(t["due"])) and d < today and not is_done(t["status"])
            if overdue or ("block" in t["status"].lower() and not is_done(t["status"])):
                msg = f'Task "{t["task"]}" ({t["owner"]}) is overdue since {t["due"]}' if overdue else f'Task "{t["task"]}" ({t["owner"]}) is blocked'
                risks.append({"Risk": msg, "Category": "Schedule" if overdue else "Dependency",
                              "Mitigation": "Confirm remaining work, assign support, and agree a revised deadline or unblock plan.",
                              "Source": t["doc"], **rs.rate_task(t, today)})
        return sorted(risks, key=lambda r: -r["Score"])

class BlockerActionAgent:
    """Extract blockers, unresolved decisions, and trackable action items."""
    def run(self, kb):
        blockers = [{"Blocker": text, "Source": name} for name, text in kb.text_lines
                    if re.search(r"\bblocker\b|\bblocked\b|\bpending\b|\bunresolved\b|open issue|decision|waiting on", text, re.I)]
        blockers.extend({"Blocker": f'Task "{t["task"]}" is blocked ({t["owner"]})', "Source": t["doc"]}
                        for t in kb.tasks if "block" in t["status"].lower())
        actions = []
        for name, text in kb.text_lines:
            if re.search(r"^action\b|\b(?:to|will) (finish|set up|build|fix|review|complete|prepare|submit|test)\b", text, re.I):
                owner = re.search(r"\b([A-Z][a-z]+)\s+(?:will|to)\b", text)
                due = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", text)
                actions.append({"Action": re.sub(r"^action:?\s*", "", text, flags=re.I),
                                "Owner": owner.group(1) if owner else "Unassigned",
                                "Due": due.group(0) if due else "", "Source": name})
        actions.extend({"Action": f'{t["task"]} ({t["status"] or "open"})',
                        "Owner": t["owner"], "Due": t["due"], "Source": t["doc"]}
                       for t in kb.tasks if not re.search(r"done|complete", t["status"], re.I))
        return blockers, actions


class ForecastAgent:
    """Forecast delivery from task data: completion, overdue/blocked load, required weekly throughput."""
    def run(self, kb, today=None):
        today = today or dt.date.today()
        tasks = kb.tasks
        if not tasks:
            return {"available": False, "status": "No task data",
                    "summary": "Upload a task CSV (task, owner, status, due) to forecast delivery."}
        open_t = [t for t in tasks if not is_done(t["status"])]
        overdue = [t for t in open_t if (d := _parse_date(t["due"])) and d < today]
        blocked = [t for t in open_t if "block" in t["status"].lower()]
        dues = [d for d in (_parse_date(t["due"]) for t in tasks) if d]
        last = max(dues) if dues else None
        days_left = (last - today).days if last else None
        need = round(len(open_t) / (days_left / 7), 1) if days_left and days_left > 0 else None
        if (last and last < today and open_t) or len(overdue) / len(tasks) > .25 or len(blocked) >= 2:
            status = "Likely late"
        elif overdue or blocked or (need and need > 5):
            status = "At risk"
        else:
            status = "On track"
        pct = round(100 * (len(tasks) - len(open_t)) / len(tasks))
        text = (f"{pct}% of {len(tasks)} tasks are complete; {len(overdue)} overdue and {len(blocked)} blocked. "
                + (f"The last planned due date is {last} ({days_left} days away), requiring about {need} tasks/week. " if need
                   else f"The last planned due date was {last}. " if last else "") + f"Forecast: {status}.")
        return {"available": True, "status": status, "completion": pct, "open": len(open_t),
                "overdue": len(overdue), "blocked": len(blocked), "last_due": str(last or ""),
                "days_left": days_left, "required_per_week": need, "summary": text,
                "at_risk_tasks": [f'{t["task"]} ({t["owner"]}, due {t["due"] or "n/a"})' for t in (overdue + blocked)[:6]]}
