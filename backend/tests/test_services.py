import re

import pytest

from backend.app.core.constants import CATEGORY_MANAGER_MAP
from backend.app.core.enums import Priority, Role, Status
from backend.app.services.complaint_service import ComplaintService, generate_ticket_id
from backend.app.services.errors import (ConflictError, DomainError, InvalidInputError,
                                         InvalidTransitionError, PermissionDeniedError)
from backend.app.services.user_service import UserService
from backend.tests.conftest import TEST_PASSWORD

STRONG = "Student@123"


@pytest.fixture
def users(seeded_db):
    return UserService(seeded_db)


@pytest.fixture
def complaints(seeded_db):
    return ComplaintService(seeded_db)


@pytest.fixture
def student(users):
    return users.register_student("Priya Patel", "priya.p@college.edu", STRONG, "Computer Science")


def staff(users, user_id):
    return users.get(user_id)


# ── users ────────────────────────────────────────────────────────────────────
def test_student_ids_go_up_from_st000101(users):
    first = users.register_student("A", "a@college.edu", STRONG, "MBA")
    second = users.register_student("B", "b@college.edu", STRONG, "MBA")
    assert (first.user_id, second.user_id) == ("ST000101", "ST000102")


def test_duplicate_email_rejected(users, student):
    with pytest.raises(ConflictError):
        users.register_student("Other", "PRIYA.P@college.edu ", STRONG, "MBA")


def test_weak_password_rejected(users):
    with pytest.raises(InvalidInputError):
        users.register_student("Weak", "weak@college.edu", "password", "MBA")


def test_login(users, student):
    assert users.login("ST000101", STRONG).id == student.id
    assert users.login("ST000101", "Wrong@123") is None
    assert users.login("ADMIN001", TEST_PASSWORD).role == Role.ADMIN


# ── submit + routing ─────────────────────────────────────────────────────────
def test_ticket_id_format():
    for _ in range(50):
        assert re.fullmatch(r"TKT-[A-Z]{3}\d{5}", generate_ticket_id())


@pytest.mark.parametrize("category,manager_id", CATEGORY_MANAGER_MAP.items())
def test_routed_to_category_manager(complaints, student, category, manager_id):
    complaint = complaints.submit(student, "Some issue", "details here", category)
    assert complaint.manager.user_id == manager_id
    assert complaint.status == Status.ASSIGNED


def test_submit_writes_history(complaints, student):
    complaint = complaints.submit(student, "Fan not working", "room 12", "Infrastructure")
    actions = [(h.action, h.old_status, h.new_status) for h in complaint.history]
    assert actions == [("Complaint Submitted", None, Status.PENDING),
                       ("Assigned", Status.PENDING, Status.ASSIGNED)]


def test_critical_gets_meet_link(complaints, student):
    complaint = complaints.submit(student, "Ragging", "in hostel block A", "Ragging")
    assert complaint.priority == Priority.CRITICAL
    assert complaint.meet_link


def test_stays_pending_when_manager_not_seeded(db):
    # empty db: no managers at all
    student = UserService(db).register_student("Solo", "solo@college.edu", STRONG, "MBA")
    complaint = ComplaintService(db).submit(student, "Wifi", "slow", "IT/Internet")
    assert complaint.status == Status.PENDING and complaint.manager is None


def test_unknown_category_rejected(complaints, student):
    with pytest.raises(InvalidInputError):
        complaints.submit(student, "x", "y", "Parking")


# ── status changes ───────────────────────────────────────────────────────────
def test_full_flow_to_closed(users, complaints, student):
    gm = staff(users, "GM002")
    admin = staff(users, "ADMIN001")
    t = complaints.submit(student, "Fan broken", "room 5", "Infrastructure").ticket_id

    complaints.update_status(t, "In Progress", gm, "electrician called")
    complaints.update_status(t, "Resolved", gm, "fan replaced")
    complaints.request_close(t, gm)
    closed = complaints.admin_close(t, admin)

    assert closed.status == Status.CLOSED and not closed.close_requested
    assert [h.new_status for h in closed.history if h.new_status] == [
        Status.PENDING, Status.ASSIGNED, Status.IN_PROGRESS, Status.RESOLVED, Status.CLOSED]


def test_manager_cannot_skip_to_resolved(users, complaints, student):
    t = complaints.submit(student, "Fan", "room 5", "Infrastructure").ticket_id
    with pytest.raises(InvalidTransitionError):
        complaints.update_status(t, "Resolved", staff(users, "GM002"))


def test_manager_cannot_close(users, complaints, student):
    gm = staff(users, "GM002")
    t = complaints.submit(student, "Fan", "room 5", "Infrastructure").ticket_id
    complaints.update_status(t, "In Progress", gm)
    complaints.update_status(t, "Resolved", gm)
    with pytest.raises(InvalidTransitionError):
        complaints.update_status(t, "Closed", gm)


def test_other_manager_cannot_touch(users, complaints, student):
    t = complaints.submit(student, "Fan", "room 5", "Infrastructure").ticket_id
    with pytest.raises(PermissionDeniedError):
        complaints.update_status(t, "In Progress", staff(users, "GM001"))


def test_reopen_clears_close_request(users, complaints, student):
    gm = staff(users, "GM002")
    t = complaints.submit(student, "Fan", "room 5", "Infrastructure").ticket_id
    complaints.update_status(t, "In Progress", gm)
    complaints.update_status(t, "Resolved", gm)
    complaints.request_close(t, gm)
    reopened = complaints.update_status(t, "In Progress", gm, "still not working")
    assert not reopened.close_requested and reopened.resolved_at is None


def test_admin_needs_close_request_unless_forced(users, complaints, student):
    gm, admin = staff(users, "GM002"), staff(users, "ADMIN001")
    t = complaints.submit(student, "Fan", "room 5", "Infrastructure").ticket_id
    complaints.update_status(t, "In Progress", gm)
    complaints.update_status(t, "Resolved", gm)
    with pytest.raises(DomainError):
        complaints.admin_close(t, admin)
    closed = complaints.admin_close(t, admin, force=True)
    assert closed.history[-1].action == "Admin Force Closed"


def test_request_close_only_when_resolved(users, complaints, student):
    t = complaints.submit(student, "Fan", "room 5", "Infrastructure").ticket_id
    with pytest.raises(InvalidTransitionError):
        complaints.request_close(t, staff(users, "GM002"))


def test_stats(users, complaints, student):
    complaints.submit(student, "Ragging", "hostel", "Ragging")
    complaints.submit(student, "Fan", "room 5", "Infrastructure")
    stats = complaints.stats()
    assert stats["Total"] == 2 and stats["Assigned"] == 2
    assert stats["Students"] == 1 and stats["OpenCritical"] == 1
