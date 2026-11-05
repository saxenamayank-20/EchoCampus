"""phase 5: the langgraph intake graph, the closure graph (pause/resume) and weekly insights"""
import pytest

from backend.app.agents.intake_graph import build_intake_graph, run_intake
from backend.app.ai.llm_client import LLMClient
from backend.app.core.enums import Priority, Status
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.notification_service import NotificationService
from backend.app.services.user_service import UserService
from backend.tests.conftest import FakeLLM


class CrashingLLM(LLMClient):
    """not an LLMError: a bug or a network library blowing up"""
    def generate_json(self, feature, prompt, schema):
        raise RuntimeError("boom")

    def embed(self, feature, texts):
        raise RuntimeError("boom")


@pytest.fixture
def students(seeded_db):
    users = UserService(seeded_db)
    return [users.register_student(f"S{i}", f"s{i}@college.edu", "Student@123", "MBA") for i in range(2)]


def history_actions(complaint):
    return [h.action for h in complaint.history]


# ── intake graph ─────────────────────────────────────────────────────────────
def test_normal_complaint_skips_escalate(seeded_db, students):
    service = ComplaintService(seeded_db)
    state = run_intake(service, students[0], "Wifi slow", "library wifi is slow", "IT/Internet")
    assert state["steps"] == ["classify", "check_duplicates", "route", "notify"]
    c = service.complaints.get_by_ticket(state["ticket_id"])
    assert c.status == Status.ASSIGNED and c.manager.user_id == "GM102" and not c.meet_link
    assert NotificationService(seeded_db).list_for(c.student)[0].type == "submitted"


def test_critical_complaint_goes_through_escalate(seeded_db, students):
    service = ComplaintService(seeded_db)
    state = run_intake(service, students[0], "Ragging", "seniors ragging in hostel", "Ragging")
    assert state["steps"] == ["classify", "check_duplicates", "route", "escalate", "notify"]
    c = service.complaints.get_by_ticket(state["ticket_id"])
    assert c.priority == Priority.CRITICAL and c.meet_link
    assert "Critical Escalation" in history_actions(c)
    admin = UserService(seeded_db).get("AD100")
    assert NotificationService(seeded_db).list_for(admin)[0].type == "critical_filed"


def test_crashing_ai_never_blocks_a_submission(seeded_db, students):
    service = ComplaintService(seeded_db, llm=CrashingLLM())
    c = service.submit(students[0], "Exam result missing", "sem 5 result not shown", "Examination")
    assert c.status == Status.ASSIGNED and c.priority_source == "keyword" and c.embedding is None


def test_duplicates_found_on_submit_are_logged(seeded_db, students):
    service = ComplaintService(seeded_db, llm=FakeLLM())
    first = service.submit(students[0], "Wifi down block B", "no wifi in hostel block B rooms", "IT/Internet")
    second = service.submit(students[1], "Block B wifi down", "hostel block B rooms have no wifi", "IT/Internet")
    found = [h for h in second.history if h.action == "Similar Complaints Found"]
    assert found and first.ticket_id in found[0].note


def test_graph_diagram_has_all_nodes():
    mermaid = build_intake_graph(None).get_graph().draw_mermaid()
    for node in ("classify", "check_duplicates", "route", "escalate", "notify"):
        assert node in mermaid


# ── closure graph (human in the loop) ────────────────────────────────────────
@pytest.fixture
def flow(seeded_db, students):
    """a resolved complaint with a close request: the graph is paused, waiting for the student"""
    service = ComplaintService(seeded_db)
    users = UserService(seeded_db)
    gm, admin = users.get("GM102"), users.get("AD100")
    c = service.submit(students[0], "Wifi slow", "library wifi is slow", "IT/Internet")
    service.update_status(c.ticket_id, "In Progress", gm)
    service.update_status(c.ticket_id, "Resolved", gm)
    service.request_close(c.ticket_id, gm, "New router installed")
    return {"service": service, "t": c.ticket_id, "c": c, "gm": gm, "admin": admin, "student": students[0]}


def waiting(f):
    return f["service"].closure_state(f["t"])["waiting_at"]


def test_graph_pauses_for_student_then_admin(flow):
    assert waiting(flow) == "await_student"
    flow["service"].student_respond(flow["t"], flow["student"], fixed=True, rating=5)
    assert waiting(flow) == "await_admin"                 # second pause
    flow["service"].admin_close(flow["t"], flow["admin"])
    assert waiting(flow) is None and flow["c"].status == Status.CLOSED
    assert flow["c"].latest_confirmation.admin_decision == "approved"


def test_dispute_ends_the_round_and_a_new_request_starts_a_new_thread(flow):
    s = flow["service"]
    s.student_respond(flow["t"], flow["student"], fixed=False, reason="still slow")
    first = s.closure_state(flow["t"])
    assert first["waiting_at"] is None and flow["c"].status == Status.IN_PROGRESS
    s.update_status(flow["t"], "Resolved", flow["gm"])
    s.request_close(flow["t"], flow["gm"], "Second access point added")
    second = s.closure_state(flow["t"])
    assert second["thread"] != first["thread"] and second["waiting_at"] == "await_student"


def test_auto_confirm_resumes_the_graph(flow, seeded_db):
    from datetime import timedelta

    from backend.app.db.base import now
    from backend.app.services.confirmation_service import ConfirmationService
    from backend.tests.conftest import FakeSender
    assert ConfirmationService(seeded_db, FakeSender()).auto_confirm_due(at=now() + timedelta(days=4)) == [flow["t"]]
    assert waiting(flow) == "await_admin" and flow["c"].latest_confirmation.student_response == "auto_confirmed"


def test_admin_override_while_waiting_for_student(flow):
    flow["service"].admin_close(flow["t"], flow["admin"], force=True, reason="Checked on site myself")
    assert waiting(flow) is None and flow["c"].status == Status.CLOSED
    assert flow["c"].latest_confirmation.admin_decision == "override"


def test_manager_reopening_ends_the_paused_graph(flow):
    flow["service"].update_status(flow["t"], "In Progress", flow["gm"], "Found another issue")
    assert waiting(flow) is None and flow["c"].latest_confirmation.student_response == "withdrawn"


def test_no_paused_graph_still_works(flow):
    """sqlite + a backend restart loses the memory saver: the same step runs directly"""
    from backend.app.agents.checkpointer import reset_checkpointer
    reset_checkpointer()
    service = ComplaintService(flow["service"].db)          # a new request after the restart
    service.student_respond(flow["t"], flow["student"], fixed=True)
    service.admin_close(flow["t"], flow["admin"])
    assert flow["c"].status == Status.CLOSED


def test_closure_diagram_has_both_pauses():
    from backend.app.agents.closure_graph import build_closure_graph
    mermaid = build_closure_graph(None).get_graph().draw_mermaid()
    assert "await_student" in mermaid and "await_admin" in mermaid


# ── weekly insights ──────────────────────────────────────────────────────────
from backend.app.agents.insights import numbers_ok, run_weekly_insights, weekly_stats  # noqa: E402


@pytest.fixture
def week(seeded_db, students):
    service = ComplaintService(seeded_db)
    for title, cat in [("Wifi slow", "IT/Internet"), ("Wifi down", "IT/Internet"), ("Fan broken", "Hostel")]:
        service.submit(students[0], title, "please fix it", cat)
    return seeded_db


def test_stats_come_from_the_database(week):
    s = weekly_stats(week)
    assert s["complaints_this_week"] == 3 and s["complaints_last_week"] == 0 and s["change_percent"] is None
    assert s["by_category"][0] == {"category": "IT/Internet", "this_week": 2, "last_week": 0, "change": 2}


def test_ai_report_is_saved_when_its_numbers_are_real(week):
    llm = FakeLLM({"insights": {"lines": ["3 complaints this week, 0 last week.", "IT/Internet had 2."]}})
    r = run_weekly_insights(week, llm)
    assert r.used_ai and r.report.splitlines()[0] == "3 complaints this week, 0 last week."


def test_made_up_number_falls_back_to_the_template(week):
    llm = FakeLLM({"insights": {"lines": ["Complaints went up by 45% this week."]}})   # 45 isn't in the stats
    r = run_weekly_insights(week, llm)
    assert not r.used_ai and r.report.startswith("3 complaints this week, 0 last week")


def test_ai_down_still_gives_a_report(week):
    r = run_weekly_insights(week, FakeLLM(fail=True))
    assert not r.used_ai and "SLA breaches" in r.report


def test_numbers_check():
    stats = {"a": 12, "by_category": [{"category": "Hostel", "this_week": 5, "last_week": 2, "change": 3}]}
    assert numbers_ok(["12 complaints, Hostel up by 3"], stats)
    assert not numbers_ok(["13 complaints"], stats)


def test_insights_api(client):
    from backend.tests.conftest import login
    admin = login(client, "AD100")
    r = client.post("/admin/insights/run", headers=admin)
    assert r.status_code == 200 and r.json()["lines"] and r.json()["used_ai"] is False   # no ai in tests
    assert len(client.get("/admin/insights", headers=admin).json()) == 1
    assert client.post("/admin/insights/run", headers=login(client, "GM101")).status_code == 403
