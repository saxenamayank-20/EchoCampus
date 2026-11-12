"""forgot details: recovery code -> student id, login code -> sign in -> set a new password"""
from datetime import timedelta

from backend.app.core.config import settings
from backend.app.models import EmailOtp
from backend.tests.conftest import STUDENT_PASSWORD, login, make_student

EMAIL = "student1@college.edu"


def test_forgot_id_with_recovery_code(client, mailbox):
    uid, _ = make_student(client, mailbox)
    r = client.post("/auth/forgot/id", json={"email": EMAIL})
    assert r.status_code == 200 and "recovery code" in mailbox.sent[-1][1]
    code = mailbox.last_code()
    r = client.post("/auth/forgot/id/verify", json={"email": EMAIL, "code": code})
    assert r.status_code == 200 and r.json()["user_id"] == uid
    # one time only
    assert client.post("/auth/forgot/id/verify", json={"email": EMAIL, "code": code}).status_code == 422


def test_unknown_email_gets_the_same_answer_and_no_mail(client, mailbox):
    make_student(client, mailbox)
    sent = len(mailbox.sent)
    known = client.post("/auth/forgot/id", json={"email": EMAIL}).json()
    unknown = client.post("/auth/forgot/id", json={"email": "nobody@college.edu"}).json()
    assert known == unknown
    assert len(mailbox.sent) == sent + 1     # only the real student got a mail


def test_forgot_password_login_code_then_new_password(client, mailbox):
    uid, _ = make_student(client, mailbox)
    assert client.post("/auth/forgot/password", json={"user_id": uid}).status_code == 200
    assert "login code" in mailbox.sent[-1][1]
    code = mailbox.last_code()
    r = client.post("/auth/login-code", json={"user_id": uid, "code": code})
    assert r.status_code == 200 and r.json()["code_login"] is True
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    # the same code can't sign in twice
    assert client.post("/auth/login-code", json={"user_id": uid, "code": code}).status_code == 422

    # no old password needed in this session
    r = client.post("/auth/change-password", json={"new_password": "Fresh@2026"}, headers=h)
    assert r.status_code == 200 and r.json()["access_token"]
    assert "password was changed" in mailbox.sent[-1][1]
    login(client, uid, "Fresh@2026")
    assert client.post("/auth/login", json={"user_id": uid, "password": STUDENT_PASSWORD}).status_code == 401


def test_normal_session_still_needs_the_old_password(client, mailbox):
    _, h = make_student(client, mailbox)
    r = client.post("/auth/change-password", json={"new_password": "Fresh@2026"}, headers=h)
    assert r.status_code == 422 and "Current password" in r.json()["error"]["message"]


def test_codes_only_work_for_their_own_purpose(client, mailbox):
    uid, _ = make_student(client, mailbox)
    client.post("/auth/forgot/id", json={"email": EMAIL})
    recovery = mailbox.last_code()
    # a recovery code can't sign you in
    assert client.post("/auth/login-code", json={"user_id": uid, "code": recovery}).status_code == 422
    client.post("/auth/forgot/password", json={"user_id": uid})
    login_code = mailbox.last_code()
    # and a login code doesn't reveal the id
    assert client.post("/auth/forgot/id/verify", json={"email": EMAIL, "code": login_code}).status_code == 422


def test_login_code_expires(client, mailbox, seeded_db):
    uid, _ = make_student(client, mailbox)
    client.post("/auth/forgot/password", json={"user_id": uid})
    code = mailbox.last_code()
    otp = seeded_db.query(EmailOtp).filter_by(purpose="login").one()
    otp.expires_at -= timedelta(minutes=settings.otp_expire_minutes + 1)
    seeded_db.commit()
    r = client.post("/auth/login-code", json={"user_id": uid, "code": code})
    assert r.status_code == 422 and "expired" in r.json()["error"]["message"]


def test_staff_are_sent_to_the_admin(client):
    r = client.post("/auth/forgot/password", json={"user_id": "GM101"})
    assert r.status_code == 403 and "contact the admin" in r.json()["error"]["message"]
    assert client.post("/auth/login-code", json={"user_id": "GM101", "code": "123456"}).status_code == 401


def test_daily_limit_then_contact_the_tech_team(client, mailbox):
    uid, _ = make_student(client, mailbox)
    for _ in range(settings.recovery_codes_per_day):
        assert client.post("/auth/forgot/password", json={"user_id": uid}).status_code == 200
    # forgot id counts for the same account
    r = client.post("/auth/forgot/id", json={"email": EMAIL})
    assert r.status_code == 429 and "technical team" in r.json()["error"]["message"]
