"""phase 6: the admin's ai usage numbers come from the llm_calls log"""
from datetime import timedelta

from backend.app.ai.usage import ai_usage, p95
from backend.app.db.base import now
from backend.app.models import LLMCall
from backend.tests.conftest import login


def add_calls(db):
    rows = [("triage", 400, True, 100, 20), ("triage", 600, True, 120, 30), ("triage", 900, False, None, None),
            ("embedding", 200, True, 50, None)]
    for feature, ms, ok, tin, tout in rows:
        db.add(LLMCall(feature=feature, model="m", latency_ms=ms, success=ok, input_tokens=tin, output_tokens=tout,
                       error=None if ok else "429 too many requests"))
    # too old for the last 30 days
    db.add(LLMCall(feature="rag", model="m", latency_ms=100, success=True, created_at=now() - timedelta(days=40)))
    db.commit()


def test_usage_per_feature(seeded_db):
    add_calls(seeded_db)
    u = ai_usage(seeded_db, days=30)
    assert u["total"]["calls"] == 4 and u["total"]["failed"] == 1 and u["total"]["success_rate"] == 75
    triage = u["by_feature"][0]
    assert triage["feature"] == "triage" and triage["calls"] == 3
    assert triage["avg_ms"] == 500                 # failed calls don't count for speed
    assert triage["input_tokens"] == 220 and triage["output_tokens"] == 50
    assert u["recent_errors"][0]["error"] == "429 too many requests"
    assert "rag" not in [r["feature"] for r in u["by_feature"]]


def test_no_calls_yet(seeded_db):
    u = ai_usage(seeded_db)
    assert u["total"]["calls"] == 0 and u["total"]["success_rate"] is None and u["by_feature"] == []


def test_p95():
    assert p95([]) is None
    assert p95(list(range(1, 101))) == 95
    assert p95([700]) == 700


def test_ai_usage_api_is_admin_only(client):
    assert client.get("/admin/ai-usage", headers=login(client, "AD100")).status_code == 200
    assert client.get("/admin/ai-usage", headers=login(client, "GM101")).status_code == 403
    assert client.get("/admin/ai-usage?days=0", headers=login(client, "AD100")).status_code == 422
