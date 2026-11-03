from datetime import datetime

from pydantic import BaseModel

from backend.app.models import InsightReport


class InsightOut(BaseModel):
    id: int
    period_start: datetime
    period_end: datetime
    lines: list[str]
    used_ai: bool
    created_at: datetime

    @classmethod
    def of(cls, r: InsightReport) -> "InsightOut":
        return cls(id=r.id, period_start=r.period_start, period_end=r.period_end,
                   lines=r.report.splitlines(), used_ai=r.used_ai, created_at=r.created_at)
