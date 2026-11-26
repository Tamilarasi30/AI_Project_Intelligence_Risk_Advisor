"""Module 8 - Conversational assistant grounded in uploaded documents (rules + RAG; optional Claude synthesis)."""
import json, os, re

def _rules(kb, a, q):
    h, f = a["health"], a["forecast"]
    if re.search(r"on track|health|status|progress", q, re.I):
        return (f"Overall project health is {h['overall']}/100 ({h['label']}). Scope clarity {h['scope']}, timeline safety {h['timeline']}, "
                f"blocker score {h['blockers']}. {len(a['risks'])} risks and {len(a['blockers'])} blockers found. {f['summary']}")
    if re.search(r"forecast|deliver|deadline|finish|late|when", q, re.I):
        return f["summary"] + ("\nAt-risk tasks:\n" + "\n".join(f"- {t}" for t in f["at_risk_tasks"]) if f.get("at_risk_tasks") else "")
    if re.search(r"\brisk", q, re.I):
        return ("Top risks:\n" + "\n".join(f'{i}. [{r["Level"]}] {r["Risk"]} (source: {r["Source"]}). Action: {r["Mitigation"]}'
                for i, r in enumerate(a["risk_register"][:5], 1))) if a["risks"] else "No risks were identified in the uploaded documents."
    if re.search(r"blocker|pending|unresolved|decision", q, re.I):
        return ("Blockers and pending decisions:\n" + "\n".join(f'{i}. {b["Blocker"]} (source: {b["Source"]})'
                for i, b in enumerate(a["blockers"][:6], 1))) if a["blockers"] else "No blockers were identified."
    if re.search(r"action|to.?do|next steps?", q, re.I):
        return ("Open action items:\n" + "\n".join(f'{i}. [{x["Priority"]}] {x["Action"]} - {x["Owner"]}, due {x["Due"] or "n/a"} (source: {x["Source"]})'
                for i, x in enumerate(a["action_items"][:8], 1))) if a["actions"] else "No open action items were identified."
    if re.search(r"scope|goal|milestone|deliverable", q, re.I) and a["goals"]:
        return "Goals and deliverables:\n" + "\n".join(f"- {t} (source: {n})" for n, t in a["goals"][:6]) + \
               "\nMilestones:\n" + "\n".join(f"- {t} (source: {n})" for n, t in a["dates"][:5])
    if re.search(r"\bwho\b|owner|team", q, re.I) and a["owners"]:
        return "Team members found in the documents: " + ", ".join(a["owners"])
    return None

def _llm(a, evidence, q):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key or not evidence:
        return None
    try:
        import anthropic
        brief = {k: a[k] for k in ("health", "forecast")} | {"top_risks": [r["Risk"] for r in a["risk_register"][:5]]}
        ctx = "\n".join(f"[{c[0]}] {c[1]}" for c, _ in evidence)
        r = anthropic.Anthropic(api_key=key).messages.create(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"), max_tokens=600,
            system="Answer using ONLY the project summary and excerpts provided. Cite sources as [file]. If the answer is not present, say so.",
            messages=[{"role": "user", "content": f"SUMMARY: {json.dumps(brief)}\nEXCERPTS:\n{ctx}\n\nQUESTION: {q}"}])
        return r.content[0].text
    except Exception:
        return None

def answer(kb, a, q):
    evidence = [(c, s) for c, s in kb.search(q, k=5) if s >= 0.12]
    out = _llm(a, evidence, q) or _rules(kb, a, q)
    if out:
        if "source" not in out.lower() and "[" not in out:
            out += "\nBased on: " + ", ".join(d["name"] for d in kb.docs)
        return out
    if not evidence:
        return "I couldn't find supporting information in the uploaded project documents. Try asking about a named feature, milestone, owner, date, risk or task."
    return "Relevant evidence from your uploaded documents:\n" + "\n".join(f"- {c[1]} (source: {c[0]}, relevance: {s:.2f})" for c, s in evidence[:4])
