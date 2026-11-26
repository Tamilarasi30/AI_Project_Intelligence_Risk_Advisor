"""Risk level identification: likelihood x impact matrix (5x5) built from explainable evidence signals.

Likelihood (1-5): certainty cues, hedging, corroboration by other documents, overdue evidence.
Impact (1-5): category baseline, severity cues, minimisers, task priority / days overdue.
Score = L x I (1-25): >=15 High, >=8 Medium, else Low. Resolved/negated statements are not risks.
"""
import re

CATEGORY_IMPACT = {"Schedule": 4, "Technical": 4, "Budget": 4, "Dependency": 3, "Scope": 3, "Resource": 3, "Quality": 2}
CERTAIN = re.compile(r"\b(still|already|currently|not fixed|not yet|missed|overdue|has been|have been)\b|\b(is|are|was|were) (now )?(delayed|late|behind|blocked|down|failing)\b", re.I)
HEDGE = re.compile(r"\b(may|might|could|possibly|potential(ly)?|if|perhaps|worried|concern)\b", re.I)
SEVERE = re.compile(r"\b(critical|severe|major|blocker|blocking|showstopper|entire|all users|production|release|launch|demo|deadline|security|data loss|legal|compliance)\b|\b(two|three|four|[2-9]) weeks\b", re.I)
MINOR = re.compile(r"\b(minor|small|cosmetic|trivial|slight|nice to have)\b", re.I)
RESOLVED = re.compile(r"(?<!not )(?<!yet )(?<!un)\b(resolved|fixed|closed|mitigated|solved)\b|\bno longer\b|\bnot an issue\b|\bno risk\b", re.I)
_clamp = lambda v: max(1, min(5, v))
_label = lambda v: "Low" if v <= 2 else "Medium" if v == 3 else "High"

def level(score):
    return "High" if score >= 15 else "Medium" if score >= 8 else "Low"

def _tokens(t):
    return set(re.findall(r"[a-z]{4,}", t.lower()))

def corroboration(text, category, source, candidates):
    """Number of OTHER documents reporting a similar risk in the same category."""
    a = _tokens(text)
    return len({s for s, t, c, *_ in candidates if s != source and c == category
                and a and len(a & _tokens(t)) / len(a | _tokens(t)) >= .2})

def _pack(L, I, basis):
    s = L * I
    return {"L": L, "I": I, "Score": s, "Level": level(s), "Likelihood": _label(L), "Impact": _label(I), "Basis": "; ".join(basis)}

def rate_text(text, category, corroborated=0):
    """Return rating dict, or None when the sentence is a resolved / negated statement."""
    if RESOLVED.search(text):
        return None
    L, I, basis = 3, CATEGORY_IMPACT.get(category, 3), []
    if CERTAIN.search(text): L += 2; basis.append("certain/ongoing wording (+2 L)")
    if HEDGE.search(text): L -= 1; basis.append("hedged wording (-1 L)")
    if corroborated: L += 1; basis.append("reported in several documents (+1 L)")
    if SEVERE.search(text): I += 1; basis.append("severity cue (+1 I)")
    L, I = _clamp(L), _clamp(I)
    if MINOR.search(text): I = min(I, 2); basis.append("minor issue (I capped at 2)")
    return _pack(L, I, basis or ["default likelihood, category impact"])

def rate_task(task, today):
    """Rate an overdue or blocked task from structured data (dates and priority)."""
    from .ingestion import _parse_date
    pr = (task.get("priority") or "").lower()
    bump = 1 if pr in ("high", "critical", "p1") else -1 if pr in ("low", "p3") else 0
    due = _parse_date(task["due"])
    if due and due < today:
        days = (today - due).days
        return _pack(5, _clamp(3 + (days > 14) + bump), [f"{days} days overdue (L=5)", f"priority '{pr or 'n/a'}'"])
    return _pack(4, _clamp(3 + bump), ["task status is blocked (L=4)", f"priority '{pr or 'n/a'}'"])
