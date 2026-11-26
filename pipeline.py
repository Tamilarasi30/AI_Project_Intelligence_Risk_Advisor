"""Multi-agent pipeline: runs the specialist agents, then documentation generation and health scoring."""
from .agents import ScopeAgent, RiskAgent, BlockerActionAgent, ForecastAgent
from . import docgen, health

def analyze(kb, today=None):
    scope = ScopeAgent().run(kb)
    risks = RiskAgent().run(kb, today)
    blockers, actions = BlockerActionAgent().run(kb)
    forecast = ForecastAgent().run(kb, today)
    stories = docgen.user_stories(scope["goals"])
    return {**scope, "risks": risks, "blockers": blockers, "actions": actions, "forecast": forecast,
            "user_stories": stories, "stories": [f'{s["id"]}: {s["story"]}' for s in stories],
            "risk_register": docgen.risk_register(risks), "action_items": docgen.action_items(actions, today),
            "health": health.score(kb, scope, risks, blockers, forecast),
            "agents": {"scope": "completed", "risk_forecast": "completed", "blocker_action": "completed", "docgen": "completed"},
            "retrieval_mode": kb.retrieval_mode,
            "retrieval_note": "Semantic embeddings + ChromaDB" if kb.retrieval_mode == "semantic-chromadb"
                              else "TF-IDF fallback (install semantic dependencies and allow model download for semantic mode)"}
