"""Background jobs inside the backend process: every 15 minutes, and the weekly report."""
from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.agents.insights import run_weekly_insights
from backend.app.ai.llm_client import get_llm
from backend.app.db.session import SessionLocal
from backend.app.services.confirmation_service import ConfirmationService
from backend.app.services.sla_service import SlaService


def run_periodic_jobs() -> None:
    # jobs run outside any request, so they open their own db session
    try:
        with SessionLocal() as db:
            escalated = SlaService(db).escalate_overdue()
            confirmations = ConfirmationService(db)
            reminded = confirmations.send_reminders()
            auto = confirmations.auto_confirm_due()
            if escalated or reminded or auto:
                print(f"[JOBS] escalated {len(escalated)}, reminders {reminded}, auto-confirmed {len(auto)}")
    except Exception as e:  # a failing job must never kill the scheduler thread
        print(f"[JOBS] periodic job failed: {e}")


def run_weekly_job() -> None:
    try:
        with SessionLocal() as db:
            report = run_weekly_insights(db, get_llm())
            print(f"[JOBS] weekly report saved ({'ai' if report.used_ai else 'template'})")
    except Exception as e:
        print(f"[JOBS] weekly report failed: {e}")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    # max_instances=1: never two runs at once. coalesce: if runs were missed, do just one
    scheduler.add_job(run_periodic_jobs, "interval", minutes=15, id="periodic",
                      max_instances=1, coalesce=True)
    # monday 8 am, for the week that just ended
    scheduler.add_job(run_weekly_job, "cron", day_of_week="mon", hour=8, id="weekly_insights",
                      max_instances=1, coalesce=True)
    scheduler.start()
    return scheduler
