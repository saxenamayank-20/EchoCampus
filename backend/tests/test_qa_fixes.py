"""bugs found in the qa pass: private complaints, supporters, priority floor, uppercase login id, email failures"""
import pytest

from backend.tests.conftest import STUDENT_PASSWORD, login, make_student

WIFI = {"title": "Wifi not working hostel block B", "description": "wifi down hostel block B rooms since monday",
        "category": "IT/Internet"}
HARASS = {"title": "Senior harassing me in hostel", "description": "a senior in hostel B keeps threatening me at night",
          "category": "Harassment"}
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@pytest.fixture
def two_students(ai_client, mailbox):
    a_id, a = make_student(ai_client, mailbox, "a@college.edu")
    b_id, b = make_student(ai_client, mailbox, "b@college.edu")
    return a_id, a, b_id, b


def test_private_complaint_is_never_suggested_or_joinable(ai_client, two_students):
    _, a, _, b = two_students
    t = ai_client.post("/complaints", json=HARASS, headers=a).json()["ticket_id"]
    near = {**HARASS, "title": "Senior harassing juniors in hostel"}
    assert ai_client.post("/complaints/preview", json=near, headers=b).json()["duplicates"] == []
    assert ai_client.post(f"/complaints/{t}/support", headers=b).status_code == 403
    assert ai_client.get(f"/complaints/{t}", headers=b).status_code in (403, 404)


def test_supporter_does_not_see_who_filed_it(ai_client, two_students):
    a_id, a, _, b = two_students
    t = ai_client.post("/complaints", json=WIFI, headers=a).json()["ticket_id"]
    ai_client.post(f"/complaints/{t}/support", headers=b)
    seen = ai_client.get(f"/complaints/{t}", headers=b).json()
    assert seen["student_name"] == "Another student" and seen["student_id"] == "" and seen["student_dept"] is None
    assert a_id not in str(ai_client.get(f"/complaints/{t}/timeline", headers=b).json())
    # the owner still sees their own name
    assert ai_client.get(f"/complaints/{t}", headers=a).json()["student_id"] == a_id


def test_supporter_cant_see_or_add_proof_files(ai_client, two_students):
    _, a, _, b = two_students
    t = ai_client.post("/complaints", json=WIFI, headers=a).json()["ticket_id"]
    ai_client.post(f"/complaints/{t}/support", headers=b)
    att = ai_client.post(f"/complaints/{t}/attachments", files={"file": ("p.pdf", PDF, "application/pdf")}, headers=a)
    assert att.status_code == 201
    assert ai_client.get(f"/complaints/{t}/attachments", headers=b).json() == []
    assert ai_client.get(f"/attachments/{att.json()['id']}", headers=b).status_code == 403
    r = ai_client.post(f"/complaints/{t}/attachments", files={"file": ("p.pdf", PDF, "application/pdf")}, headers=b)
    assert r.status_code == 403


def test_manager_and_admin_see_supporter_names(ai_client, two_students):
    _, a, b_id, b = two_students
    t = ai_client.post("/complaints", json=WIFI, headers=a).json()["ticket_id"]
    ai_client.post(f"/complaints/{t}/support", headers=b)
    for staff in ("GM102", "AD100"):
        sup = ai_client.get(f"/complaints/{t}", headers=login(ai_client, staff)).json()["supporters"]
        assert [s["user_id"] for s in sup] == [b_id] and sup[0]["name"] == "Priya"
    # students never get the list
    assert ai_client.get(f"/complaints/{t}", headers=a).json()["supporters"] == []


def test_manager_cant_lower_harassment_below_critical(ai_client, two_students):
    _, a, _, _ = two_students
    t = ai_client.post("/complaints", json=HARASS, headers=a).json()["ticket_id"]
    gm = login(ai_client, "GM103")
    r = ai_client.post(f"/manager/complaints/{t}/priority", json={"priority": "Low"}, headers=gm)
    assert r.status_code == 422 and "at least Critical" in r.json()["error"]["message"]
    assert ai_client.get(f"/complaints/{t}", headers=gm).json()["priority"] == "Critical"


def test_login_id_must_be_uppercase(client, mailbox):
    uid, _ = make_student(client, mailbox)
    assert client.post("/auth/login", json={"user_id": uid.lower(), "password": STUDENT_PASSWORD}).status_code == 401
    assert client.post("/auth/login", json={"user_id": f" {uid} ", "password": STUDENT_PASSWORD}).status_code == 200


def test_verify_twice_doesnt_hand_out_the_id(client, mailbox):
    make_student(client, mailbox)
    r = client.post("/auth/verify-otp", json={"email": "student1@college.edu", "code": "123456"})
    assert r.status_code == 409 and "user_id" not in r.text


def test_register_when_email_fails_says_so_and_can_retry(client, mailbox, monkeypatch):
    body = {"name": "Riya", "email": "riya@college.edu", "password": STUDENT_PASSWORD, "department": "MBA"}
    monkeypatch.setattr(mailbox, "send", lambda *a: False)
    r = client.post("/auth/register", json=body)
    assert r.status_code == 503 and r.json()["error"]["code"] == "email_failed"
    monkeypatch.undo()
    # the half made account was removed, so the same email works again
    assert client.post("/auth/register", json=body).status_code == 201
