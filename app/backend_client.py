"""Streamlit talks to the backend services through here.

Each function opens a db session, calls a service and turns the result into plain
dicts with the same keys the pages already use. Phase 2 swaps this for API calls.
"""
from backend.app.core.config import settings
from backend.app.core.enums import Role
from backend.app.db.seed import seed_staff
from backend.app.db.session import SessionLocal
from backend.app.db.session import init_db as create_tables
from backend.app.models import Complaint, ComplaintHistory, ManagerUpdate, User
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.errors import DomainError
from backend.app.services.priority import KeywordPriorityDetector
from backend.app.services.user_service import UserService

_detector = KeywordPriorityDetector()


# ── turning models into dicts for the pages ──────────────────────────────────
def _user(u: User) -> dict:
    return {
        "user_id": u.user_id, "name": u.name, "email": u.email, "role": u.role.value,
        "department": u.department, "created_at": u.created_at,
        "category": ", ".join(c.category for c in u.categories) or None,
    }


def _complaint(c: Complaint) -> dict:
    student, manager = c.student, c.manager
    return {
        "ticket_id": c.ticket_id, "title": c.title, "description": c.description,
        "category": c.category, "priority": c.priority.value, "status": c.status.value,
        "student_id": student.user_id, "student_name": student.name,
        "student_email": student.email, "student_dept": student.department,
        "assigned_to": manager.user_id if manager else None,
        "manager_name": manager.name if manager else None,
        "manager_email": manager.email if manager else None,
        "student_remarks": c.student_remarks, "manager_remarks": c.manager_remarks,
        "meet_link": c.meet_link, "close_requested": int(c.close_requested),
        "created_at": c.created_at, "updated_at": c.updated_at, "resolved_at": c.resolved_at,
    }


def _history(h: ComplaintHistory) -> dict:
    return {
        "action": h.action, "timestamp": h.timestamp, "note": h.note,
        "old_status": h.old_status.value if h.old_status else None,
        "new_status": h.new_status.value if h.new_status else None,
        "changed_by": h.user.user_id if h.user else "system",
    }


def _manager_update(m: ManagerUpdate) -> dict:
    c = m.complaint
    return {
        "ticket_id": c.ticket_id, "title": c.title, "category": c.category,
        "priority": c.priority.value, "status": c.status.value,
        "manager_id": m.manager.user_id, "manager_name": m.manager.name,
        "update_text": m.update_text, "created_at": m.created_at,
    }


# ── setup ────────────────────────────────────────────────────────────────────
def init_db() -> None:
    create_tables()
    with SessionLocal() as db:
        seed_staff(db, settings.seed_passwords())


# ── auth ─────────────────────────────────────────────────────────────────────
def login_user(user_id: str, password: str) -> dict | None:
    with SessionLocal() as db:
        user = UserService(db).login(user_id, password)
        return _user(user) if user else None


def register_student(name: str, email: str, password: str, department: str) -> tuple[bool, str, str | None]:
    """returns (ok, message, new student id)"""
    with SessionLocal() as db:
        try:
            student = UserService(db).register_student(name, email, password, department)
        except DomainError as e:
            return False, str(e), None
        return True, "Registration successful!", student.user_id


def get_all_users(role: str | None = None) -> list[dict]:
    with SessionLocal() as db:
        return [_user(u) for u in UserService(db).list_users(Role(role) if role else None)]


# ── complaints ───────────────────────────────────────────────────────────────
def auto_detect_priority(title: str, description: str, category: str) -> str:
    return _detector.detect(title, description, category).value


def submit_complaint(student_id: str, title: str, description: str, category: str,
                     remarks: str = "") -> tuple[str, str, str, str | None]:
    """returns (ticket_id, manager name, priority, meet link)"""
    with SessionLocal() as db:
        student = UserService(db).get(student_id)
        c = ComplaintService(db).submit(student, title, description, category, remarks)
        manager_name = c.manager.name if c.manager else "Not assigned yet"
        return c.ticket_id, manager_name, c.priority.value, c.meet_link


def get_student_complaints(student_id: str) -> list[dict]:
    with SessionLocal() as db:
        student = UserService(db).get(student_id)
        return [_complaint(c) for c in ComplaintService(db).for_student(student)] if student else []


def get_manager_complaints(manager_uid: str, resolved: bool = False) -> list[dict]:
    with SessionLocal() as db:
        manager = UserService(db).get(manager_uid)
        if not manager:
            return []
        return [_complaint(c) for c in ComplaintService(db).for_manager(manager, resolved)]


def manager_status_options(ticket_id: str) -> list[str]:
    """current status first, then the ones a manager may move it to"""
    with SessionLocal() as db:
        service = ComplaintService(db)
        complaint = service.get(ticket_id)
        options = [complaint.status] + service.next_statuses(complaint, Role.MANAGER)
        return [s.value for s in options]


def _run(action) -> tuple[bool, str]:
    """runs a service call that changes data, turns rule errors into (False, message)"""
    with SessionLocal() as db:
        try:
            message = action(db)
        except DomainError as e:
            db.rollback()
            return False, str(e)
        return True, message


def update_complaint_status(ticket_id: str, new_status: str, manager_uid: str,
                            remark: str = "") -> tuple[bool, str]:
    def action(db):
        manager = UserService(db).get(manager_uid)
        ComplaintService(db).update_status(ticket_id, new_status, manager, remark)
        return "Status updated."
    return _run(action)


def request_close(ticket_id: str, manager_uid: str) -> tuple[bool, str]:
    def action(db):
        ComplaintService(db).request_close(ticket_id, UserService(db).get(manager_uid))
        return "Close request sent to Admin."
    return _run(action)


def admin_close_complaint(ticket_id: str, admin_id: str, force: bool = False) -> tuple[bool, str]:
    def action(db):
        ComplaintService(db).admin_close(ticket_id, UserService(db).get(admin_id), force)
        return f"{ticket_id} closed."
    return _run(action)


def add_manager_update(ticket_id: str, manager_id: str, update_text: str) -> tuple[bool, str]:
    def action(db):
        ComplaintService(db).add_manager_update(ticket_id, UserService(db).get(manager_id), update_text)
        return "Update sent."
    return _run(action)


def get_complaint_timeline(ticket_id: str) -> list[dict]:
    with SessionLocal() as db:
        try:
            return [_history(h) for h in ComplaintService(db).timeline(ticket_id)]
        except DomainError:
            return []


def get_manager_updates() -> list[dict]:
    with SessionLocal() as db:
        return [_manager_update(m) for m in ComplaintService(db).manager_updates()]


def get_all_complaints() -> list[dict]:
    with SessionLocal() as db:
        return [_complaint(c) for c in ComplaintService(db).all()]


def get_all_complaints_by_category() -> dict[str, list[dict]]:
    with SessionLocal() as db:
        grouped = ComplaintService(db).open_by_category()
        return {cat: [_complaint(c) for c in items] for cat, items in grouped.items()}


def get_resolved_complaints() -> list[dict]:
    with SessionLocal() as db:
        return [_complaint(c) for c in ComplaintService(db).resolved_or_close_requested()]


def get_stats() -> dict[str, int]:
    with SessionLocal() as db:
        return ComplaintService(db).stats()
