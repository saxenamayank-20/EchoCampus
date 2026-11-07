from datetime import timedelta

from backend.app.core.cache import MemoryCache, get_cache
from backend.app.core.config import settings
from backend.app.db.base import now
from backend.app.services.complaint_service import STATS_KEY, ComplaintService
from backend.app.services.sla_service import SlaService
from backend.app.services.user_service import UserService
from backend.tests.conftest import FakeSender, login, make_student

FAN = {"title": "Fan not working", "description": "room 12 fan is broken", "category": "Infrastructure"}


# ── cache ────────────────────────────────────────────────────────────────────
def test_memory_cache_ttl_and_incr(monkeypatch):
    import backend.app.core.cache as cache_module
    clock = [1000.0]
    monkeypatch.setattr(cache_module.time, "time", lambda: clock[0])
    c = MemoryCache()
    c.set("k", "v", ttl=60)
    assert c.get("k") == "v"
    clock[0] += 61
    assert c.get("k") is None                       # expired
    assert [c.incr("n", 10) for _ in range(3)] == [1, 2, 3]
    clock[0] += 11
    assert c.incr("n", 10) == 1                     # new window


def test_admin_stats_are_cached_and_refreshed_on_change(client, mailbox):
    _, h = make_student(client, mailbox)
    admin = login(client, "AD100")
    assert client.get("/admin/stats", headers=admin).json()["counts"]["Total"] == 0
    assert get_cache().get(STATS_KEY) is not None   # saved for 60 s
    client.post("/complaints", json=FAN, headers=h)
    assert get_cache().get(STATS_KEY) is None       # a change throws the cached copy away
    assert client.get("/admin/stats", headers=admin).json()["counts"]["Total"] == 1


# ── rate limits ──────────────────────────────────────────────────────────────
def test_complaint_rate_limit_429(client, mailbox, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_complaints_per_hour", 5)
    _, h = make_student(client, mailbox)
    for i in range(5):
        assert client.post("/complaints", json={**FAN, "title": f"Fan {i} broken"}, headers=h).status_code == 201
    r = client.post("/complaints", json=FAN, headers=h)
    assert r.status_code == 429 and r.json()["error"]["code"] == "rate_limited"


def test_login_rate_limit_per_user_429(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_logins_per_15_min", 3)
    for _ in range(3):
        client.post("/auth/login", json={"user_id": "AD100", "password": "Wrong@123"})
    r = client.post("/auth/login", json={"user_id": "ad100", "password": "Test@1234"})
    assert r.status_code == 429      # even the right password waits, that's what stops guessing
    # everyone comes from the same ip in tests (like behind render's proxy), other users can still log in
    assert client.post("/auth/login", json={"user_id": "GM101", "password": "Test@1234"}).status_code == 200


# ── sla ──────────────────────────────────────────────────────────────────────
def test_sla_due_time_follows_priority(client, mailbox):
    from datetime import datetime
    _, h = make_student(client, mailbox)
    for body, hours in [({"title": "Ragging", "description": "in hostel", "category": "Ragging"}, 4),
                        ({"title": "Water cooler", "description": "please clean it", "category": "Other"}, 168)]:
        c = client.post("/complaints", json=body, headers=h).json()
        gap = datetime.fromisoformat(c["sla_due_at"]) - datetime.fromisoformat(c["created_at"])
        assert gap == timedelta(hours=hours) and c["escalated"] is False


def test_overdue_complaints_get_escalated(seeded_db):
    users = UserService(seeded_db)
    student = users.register_student("S", "s@college.edu", "Student@123", "MBA")
    service = ComplaintService(seeded_db)
    critical = service.submit(student, "Ragging", "in hostel", "Ragging")        # 4 h sla
    low = service.submit(student, "Water cooler", "please clean", "Other")       # 168 h sla
    assert critical.sla_due_at - critical.created_at == timedelta(hours=settings.sla_hours_critical)

    mailbox = FakeSender()
    sla = SlaService(seeded_db, mailbox)
    assert sla.escalate_overdue(at=now() + timedelta(hours=1)) == []             # nothing late yet
    escalated = sla.escalate_overdue(at=now() + timedelta(hours=5))              # 5 h later
    assert [c.ticket_id for c in escalated] == [critical.ticket_id]
    assert critical.escalated and not low.escalated
    assert critical.history[-1].action == "SLA Escalated"
    assert mailbox.sent and "overdue" in mailbox.sent[0][1]
    # running again doesn't escalate the same one twice
    assert sla.escalate_overdue(at=now() + timedelta(hours=6)) == []
    assert service.stats()["Overdue"] == 1


def test_resolved_complaints_are_not_escalated(seeded_db):
    users = UserService(seeded_db)
    student = users.register_student("S", "s@college.edu", "Student@123", "MBA")
    service = ComplaintService(seeded_db)
    c = service.submit(student, "Ragging", "in hostel", "Ragging")
    gm = users.get("GM103")
    service.update_status(c.ticket_id, "In Progress", gm)
    service.update_status(c.ticket_id, "Resolved", gm)
    assert SlaService(seeded_db, FakeSender()).escalate_overdue(at=now() + timedelta(days=30)) == []


def test_escalation_notifies_admin_and_manager(client, mailbox, seeded_db):
    _, h = make_student(client, mailbox)
    t = client.post("/complaints", json={"title": "Ragging", "description": "x hostel", "category": "Ragging"},
                    headers=h).json()["ticket_id"]
    SlaService(seeded_db, FakeSender()).escalate_overdue(at=now() + timedelta(hours=5))
    admin, gm = login(client, "AD100"), login(client, "GM103")

    n = client.get("/notifications", headers=admin).json()
    # critical: one alert when filed (intake graph), one when the sla passed
    assert n["unread"] == 2 and n["items"][0]["ticket_id"] == t and n["items"][0]["type"] == "sla_escalated"
    assert n["items"][1]["type"] == "critical_filed"
    assert client.get("/notifications", headers=gm).json()["unread"] == 1
    assert client.get("/complaints?escalated=true", headers=admin).json()["total"] == 1

    client.post(f"/notifications/{n['items'][0]['id']}/read", headers=admin)
    assert client.get("/notifications", headers=admin).json()["unread"] == 1
    # someone else's notification can't be touched
    other = client.get("/notifications", headers=gm).json()["items"][0]["id"]
    assert client.post(f"/notifications/{other}/read", headers=admin).status_code == 404


def test_admin_can_run_sla_check(client, mailbox):
    admin = login(client, "AD100")
    assert client.post("/admin/sla/run", headers=admin).json() == {"escalated": []}
    _, h = make_student(client, mailbox)
    assert client.post("/admin/sla/run", headers=h).status_code == 403
