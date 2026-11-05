"""AI usage for the admin: calls, failures, tokens and speed per feature, from the llm_calls log"""
import math
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.base import now
from backend.app.models import LLMCall


def p95(values: list[int]) -> int | None:
    """the speed 95% of calls were faster than (a slow outlier doesn't hide in the average)"""
    if not values:
        return None
    values = sorted(values)
    return values[math.ceil(len(values) * 0.95) - 1]


def summarize(calls: list[LLMCall]) -> dict:
    ok = [c for c in calls if c.success]
    return {
        "calls": len(calls),
        "failed": len(calls) - len(ok),
        "success_rate": round(len(ok) * 100 / len(calls)) if calls else None,
        "avg_ms": round(sum(c.latency_ms for c in ok) / len(ok)) if ok else None,
        "p95_ms": p95([c.latency_ms for c in ok]),
        "input_tokens": sum(c.input_tokens or 0 for c in calls),
        "output_tokens": sum(c.output_tokens or 0 for c in calls),
    }


def ai_usage(db: Session, days: int = 30) -> dict:
    # a few thousand rows at most on this app, so the sums are done in python
    calls = list(db.scalars(select(LLMCall).where(LLMCall.created_at >= now() - timedelta(days=days))
                            .order_by(LLMCall.id.desc())))
    features = sorted({c.feature for c in calls})
    by_feature = [{"feature": f, **summarize([c for c in calls if c.feature == f])} for f in features]
    return {
        "days": days,
        "total": summarize(calls),
        "by_feature": sorted(by_feature, key=lambda r: -r["calls"]),
        "recent_errors": [{"feature": c.feature, "model": c.model, "error": c.error, "at": c.created_at}
                          for c in calls if not c.success][:10],
    }
