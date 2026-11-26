"""Module 7 - Project health scoring with dimension-wise breakdown."""
import re

def _clamp(v):
    return max(0, min(100, round(v)))

def score(kb, scope, risks, blockers, forecast):
    unclear = sum(bool(re.search(r"\btbd\b|unclear|undefined|ambiguous", t, re.I)) for _, t in kb.lines)
    sched = sum(r["Category"] == "Schedule" for r in risks)
    h = {"scope": _clamp(35 + 12 * min(len(scope["goals"]), 3) + 10 * bool(scope["dates"]) + 10 * bool(scope["owners"]) - 12 * unclear),
         "timeline": _clamp(100 - 18 * sched - (10 if forecast.get("status") == "Likely late" else 0)),
         "blockers": _clamp(100 - 12 * len(blockers))}
    h["overall"] = _clamp(.30 * h["scope"] + .40 * h["timeline"] + .30 * h["blockers"])
    h["label"] = "On track" if h["overall"] >= 75 else "At risk" if h["overall"] >= 50 else "Critical"
    return h
