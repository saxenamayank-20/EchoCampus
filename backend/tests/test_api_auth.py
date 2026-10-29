from datetime import timedelta

from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.models import EmailOtp
from backend.tests.conftest import STUDENT_PASSWORD, login, make_student

NEW = {"name": "Riya", "email": "riya@college.edu", "password": STUDENT_PASSWORD, "department": "MBA"}


def test_register_sends_otp_and_blocks_login_until_verified(client, mailbox):
    r = client.post("/auth/register", json=NEW)
    assert r.status_code == 201
    uid = r.json()["user_id"]
    assert uid == "ST000101"
    assert mailbox.sent[-1][0] == "riya@college.edu"

    r = client.post("/auth/login", json={"user_id": uid, "password": STUDENT_PASSWORD})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "not_verified"

    r = client.post("/auth/verify-otp", json={"user_id": uid, "code": mailbox.last_code()})
    assert r.status_code == 200
    me = client.get("/auth/me", headers=login(client, uid, STUDENT_PASSWORD)).json()
    assert me["role"] == "student" and me["is_verified"]


def test_wrong_otp_counts_attempts_then_locks(client, mailbox):
    uid = client.post("/auth/register", json=NEW).json()["user_id"]
    right = mailbox.last_code()
    wrong = "000000" if right != "000000" else "111111"
    for _ in range(settings.otp_max_attempts):
        assert client.post("/auth/verify-otp", json={"user_id": uid, "code": wrong}).status_code == 422
    # even the right code is refused now, a new one is needed
    r = client.post("/auth/verify-otp", json={"user_id": uid, "code": right})
    assert r.status_code == 422 and "new code" in r.json()["error"]["message"]


def test_expired_otp(client, mailbox, seeded_db):
    uid = client.post("/auth/register", json=NEW).json()["user_id"]
    code = mailbox.last_code()
    otp = seeded_db.query(EmailOtp).one()
    otp.expires_at -= timedelta(minutes=settings.otp_expire_minutes + 1)
    seeded_db.commit()
    r = client.post("/auth/verify-otp", json={"user_id": uid, "code": code})
    assert r.status_code == 422 and "expired" in r.json()["error"]["message"]


def test_resend_makes_old_code_useless(client, mailbox):
    uid = client.post("/auth/register", json=NEW).json()["user_id"]
    old = mailbox.last_code()
    client.post("/auth/resend-otp", json={"user_id": uid})
    new = mailbox.last_code()
    if old != new:
        assert client.post("/auth/verify-otp", json={"user_id": uid, "code": old}).status_code == 422
    assert client.post("/auth/verify-otp", json={"user_id": uid, "code": new}).status_code == 200


def test_bad_email_format_is_422(client):
    r = client.post("/auth/register", json={**NEW, "email": "not-an-email"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_email_domain_allow_list(client, monkeypatch):
    monkeypatch.setattr(settings, "allowed_email_domains", "college.edu")
    assert client.post("/auth/register", json={**NEW, "email": "x@gmail.com"}).status_code == 422
    assert client.post("/auth/register", json=NEW).status_code == 201


def test_duplicate_email_is_409(client, mailbox):
    make_student(client, mailbox, "riya@college.edu")
    assert client.post("/auth/register", json=NEW).status_code == 409


def test_wrong_password_is_401(client):
    r = client.post("/auth/login", json={"user_id": "ADMIN001", "password": "Nope@1234"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"


def test_token_carries_role_and_expiry(client):
    import jwt
    from backend.app.core.security import JWT_SECRET
    token = client.post("/auth/login", json={"user_id": "GM001", "password": "Test@1234"}).json()["access_token"]
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    assert payload["sub"] == "GM001" and payload["role"] == "grievance_manager" and "exp" in payload


def test_no_token_and_bad_token_are_401(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_expired_token_is_401(client, monkeypatch):
    monkeypatch.setattr(settings, "jwt_expire_minutes", -1)
    token = create_access_token("ADMIN001", "admin")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
