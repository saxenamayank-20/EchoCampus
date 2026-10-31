"""Background jobs that run every 15 minutes inside the backend process."""
from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.db.session import SessionLocal
from backend.app.services.sla_service import SlaService


def run_periodic_jobs() -> None:
    # jobs run outside any request, so they open their own db session
    try:
        with SessionLocal() as db:
            escalated = SlaService(db).escalate_overdue()
            if escalated:
                print(f"[JOBS] escalated {len(escalated)} overdue complaint(s)")
    except Exception as e:  # a failing job must never kill the scheduler thread
        print(f"[JOBS] periodic job failed: {e}")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    # max_instances=1: never two runs at once. coalesce: if runs were missed, do just one
    scheduler.add_job(run_periodic_jobs, "interval", minutes=15, id="periodic",
                      max_instances=1, coalesce=True)
    scheduler.start()
    return scheduler
