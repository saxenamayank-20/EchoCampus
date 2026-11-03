from datetime import timedelta

import pytest

from backend.app.db.base import now
from backend.app.services.confirmation_service import ConfirmationService
from backend.tests.conftest import FakeSender, login, make_student

FAN = {"title": "Fan not working", "description": "room 12 fan is broken", "category": "Infrastructure"}


@pytest.fixture
def resolved(client, mailbox):
    """a complaint that GM102 has resolved, plus everyone's login headers"""
    _, student = make_student(client, mailbox)
    t = client.post("/complaints", json=FAN, headers=student).json()["ticket_id"]
    gm, admin = login(client, "GM102"), login(client, "AD100")
    client.post(f"/manager/complaints/{t}/status", json={"status": "In Progress"}, headers=gm)
    client.post(f"/manager/complaints/{t}/status", json={"status": "Resolved", "remark": "fan replaced"}, headers=gm)
    return {"t": t, "student": student, "gm": gm, "admin": admin}


def close_request(client, r, note="New fan installed and tested"):
    return client.post(f"/manager/complaints/{r['t']}/close-request", json={"note": note}, headers=r["gm"])


def confirm(client, r, **body):
    return client.post(f"/complaints/{r['t']}/confirm", json=body, headers=r["student"])


def ticket(client, r):
    return client.get(f"/complaints/{r['t']}", headers=r["admin"]).json()


def actions(client, r):
    return [e["action"] for e in client.get(f"/complaints/{r['t']}/timeline", headers=r["admin"]).json()]


def test_close_request_needs_a_note(client, resolved):
    r = client.post(f"/manager/complaints/{resolved['t']}/close-request", json={"note": ""}, headers=resolved["gm"])
    assert r.status_code == 422


def test_close_request_asks_the_student(client, mailbox, resolved):
    assert close_request(client, resolved).status_code == 200
    c = ticket(client, resolved)["confirmation"]
    assert c["response"] == "pending" and c["manager_note"] == "New fan installed and tested"
    n = client.get("/notifications", headers=resolved["student"]).json()
    # 2 = "received" on submit + this one
    assert n["unread"] == 2 and "really fixed" in n["items"][0]["message"]
    assert "was" in mailbox.sent[-1][1] and "/tickets/" in mailbox.sent[-1][2]   # email with the portal link
    assert close_request(client, resolved).status_code == 409                    # already waiting


def test_confirm_path(client, resolved):
    close_request(client, resolved)
    assert confirm(client, resolved, fixed=True, rating=5).status_code == 200
    c = ticket(client, resolved)["confirmation"]
    assert c["response"] == "confirmed" and c["rating"] == 5
    assert client.get("/notifications", headers=resolved["admin"]).json()["items"][0]["type"] == "student_confirmed"
    r = client.post(f"/admin/complaints/{resolved['t']}/close", json={}, headers=resolved["admin"])
    assert r.status_code == 200 and r.json()["status"] == "Closed"
    assert ticket(client, resolved)["confirmation"]["admin_decision"] == "approved"


def test_dispute_goes_back_to_in_progress(client, resolved):
    close_request(client, resolved)
    assert confirm(client, resolved, fixed=False).status_code == 422             # reason needed
    r = confirm(client, resolved, fixed=False, reason="Fan still makes noise and stops")
    assert r.status_code == 200
    c = ticket(client, resolved)
    assert c["status"] == "In Progress" and not c["close_requested"]
    assert c["confirmation"]["response"] == "disputed"
    assert "Student Disputed" in actions(client, resolved)
    # admin and manager both hear about it
    assert client.get("/notifications", headers=resolved["gm"]).json()["items"][0]["type"] == "student_disputed"
    assert client.get("/notifications", headers=resolved["admin"]).json()["items"][0]["type"] == "student_disputed"


def test_full_round_dispute_fix_confirm_close(client, resolved):
    t, gm = resolved["t"], resolved["gm"]
    close_request(client, resolved, "Fan replaced")
    confirm(client, resolved, fixed=False, reason="still broken")
    client.post(f"/admin/complaints/{t}/message", json={"text": "Please check the wiring too"}, headers=resolved["admin"])
    assert client.get("/notifications", headers=gm).json()["items"][0]["type"] == "admin_message"
    client.post(f"/manager/complaints/{t}/status", json={"status": "Resolved", "remark": "wiring fixed"}, headers=gm)
    close_request(client, resolved, "Wiring replaced as well")                  # a new note for the new round
    confirm(client, resolved, fixed=True, rating=4)
    assert client.post(f"/admin/complaints/{t}/close", json={}, headers=resolved["admin"]).status_code == 200
    steps = actions(client, resolved)
    assert steps.count("Close Requested") == 2 and "Student Disputed" in steps and "Student Confirmed" in steps
    assert steps[-1] == "Admin Closed"


def test_admin_blocked_while_pending_and_override_is_logged(client, resolved):
    close_request(client, resolved)
    t, admin = resolved["t"], resolved["admin"]
    r = client.post(f"/admin/complaints/{t}/close", json={}, headers=admin)
    assert r.status_code == 400 and "Waiting for the student" in r.json()["error"]["message"]
    assert client.post(f"/admin/complaints/{t}/close", json={"force": True}, headers=admin).status_code == 422
    r = client.post(f"/admin/complaints/{t}/close", json={"force": True, "reason": "Verified on site visit"},
                    headers=admin)
    assert r.status_code == 200
    history = client.get(f"/complaints/{t}/timeline", headers=admin).json()
    assert history[-1]["action"] == "Admin Override Close" and history[-1]["note"] == "Verified on site visit"
    assert ticket(client, resolved)["confirmation"]["admin_decision"] == "override"


def test_only_the_owner_can_answer(client, mailbox, resolved):
    close_request(client, resolved)
    _, other = make_student(client, mailbox, "other@college.edu")
    r = client.post(f"/complaints/{resolved['t']}/confirm", json={"fixed": True}, headers=other)
    assert r.status_code == 403
    r = client.post(f"/complaints/{resolved['t']}/confirm", json={"fixed": True}, headers=resolved["gm"])
    assert r.status_code == 403        # managers can't confirm for the student


def test_nothing_to_confirm_is_409(client, resolved):
    assert confirm(client, resolved, fixed=True).status_code == 409


def test_auto_confirm_after_deadline(client, resolved, seeded_db):
    close_request(client, resolved)
    jobs = ConfirmationService(seeded_db, FakeSender())
    assert jobs.auto_confirm_due(at=now() + timedelta(days=2)) == []            # still inside 3 days
    assert jobs.auto_confirm_due(at=now() + timedelta(days=3, minutes=1)) == [resolved["t"]]
    c = ticket(client, resolved)["confirmation"]
    assert c["response"] == "auto_confirmed"
    assert "Auto Confirmed" in actions(client, resolved)
    # auto-confirmed counts like confirmed: the admin can close normally
    assert client.post(f"/admin/complaints/{resolved['t']}/close", json={}, headers=resolved["admin"]).status_code == 200


def test_reminder_one_day_before(client, resolved, seeded_db):
    close_request(client, resolved)
    mailbox = FakeSender()
    jobs = ConfirmationService(seeded_db, mailbox)
    assert jobs.send_reminders(at=now() + timedelta(hours=12)) == 0
    assert jobs.send_reminders(at=now() + timedelta(days=2, hours=1)) == 1
    assert jobs.send_reminders(at=now() + timedelta(days=2, hours=2)) == 0       # only once
    assert "please confirm" in mailbox.sent[0][1]


def test_manager_reopen_withdraws_the_request(client, resolved):
    close_request(client, resolved)
    client.post(f"/manager/complaints/{resolved['t']}/status", json={"status": "In Progress"}, headers=resolved["gm"])
    assert ticket(client, resolved)["confirmation"]["response"] == "withdrawn"
    assert confirm(client, resolved, fixed=True).status_code == 409


def test_quality_metrics(client, resolved):
    close_request(client, resolved)
    confirm(client, resolved, fixed=False, reason="not fixed")
    client.post(f"/manager/complaints/{resolved['t']}/status", json={"status": "Resolved"}, headers=resolved["gm"])
    close_request(client, resolved, "second try")
    confirm(client, resolved, fixed=True, rating=3)
    q = client.get("/admin/quality", headers=resolved["admin"]).json()
    gm2 = q["managers"][0]
    assert gm2["manager_id"] == "GM102" and gm2["close_requests"] == 2 and gm2["disputed"] == 1
    assert gm2["dispute_rate"] == 0.5 and gm2["avg_rating"] == 3
    assert q["categories"] == {"Infrastructure": 3} and q["reopened_after_close_request"] == 1


def test_after_a_dispute_the_same_note_is_refused(client, resolved):
    close_request(client, resolved, "Fan replaced")
    confirm(client, resolved, fixed=False, reason="still broken")
    client.post(f"/manager/complaints/{resolved['t']}/status", json={"status": "Resolved"}, headers=resolved["gm"])
    r = close_request(client, resolved, "fan replaced ")           # same note again (case/space don't matter)
    assert r.status_code == 422 and "new note" in r.json()["error"]["message"]
    assert close_request(client, resolved, "Replaced the regulator too").status_code == 200
