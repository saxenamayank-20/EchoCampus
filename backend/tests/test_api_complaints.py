from backend.tests.conftest import login, make_student

FAN = {"title": "Fan not working", "description": "room 12 fan is broken", "category": "Infrastructure"}


def submit(client, headers, body=FAN):
    r = client.post("/complaints", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["ticket_id"]


def test_student_submits_and_sees_own(client, mailbox):
    _, h = make_student(client, mailbox)
    t = submit(client, h)
    page = client.get("/complaints", headers=h).json()
    assert page["total"] == 1 and page["items"][0]["ticket_id"] == t
    assert page["items"][0]["manager_name"] == "Ms. Priya Sharma"


def test_student_cannot_read_another_students_ticket(client, mailbox):
    _, h1 = make_student(client, mailbox, "a@college.edu")
    _, h2 = make_student(client, mailbox, "b@college.edu")
    t = submit(client, h1)
    assert client.get(f"/complaints/{t}", headers=h2).status_code == 403
    assert client.get(f"/complaints/{t}/timeline", headers=h2).status_code == 403
    assert client.get("/complaints", headers=h2).json()["total"] == 0


def test_manager_cannot_touch_another_category(client, mailbox):
    _, h = make_student(client, mailbox)
    t = submit(client, h)                       # infrastructure -> GM002
    gm1 = login(client, "GM001")
    assert client.get(f"/complaints/{t}", headers=gm1).status_code == 403
    r = client.post(f"/manager/complaints/{t}/status", json={"status": "In Progress"}, headers=gm1)
    assert r.status_code == 403
    assert client.get("/complaints", headers=gm1).json()["total"] == 0


def test_roles_are_enforced(client, mailbox):
    _, student = make_student(client, mailbox)
    gm = login(client, "GM002")
    assert client.get("/admin/stats", headers=student).status_code == 403
    assert client.get("/admin/stats", headers=gm).status_code == 403
    assert client.post("/complaints", json=FAN, headers=gm).status_code == 403   # only students submit
    assert client.post("/manager/complaints/TKT-AAA00000/status", json={"status": "Resolved"},
                       headers=student).status_code == 403


def test_full_flow_with_status_mail(client, mailbox):
    _, h = make_student(client, mailbox)
    t = submit(client, h)
    gm, admin = login(client, "GM002"), login(client, "ADMIN001")

    assert client.get(f"/manager/complaints/{t}/status-options", headers=gm).json() == ["Assigned", "In Progress"]
    r = client.post(f"/manager/complaints/{t}/status", json={"status": "Resolved"}, headers=gm)
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_transition"

    client.post(f"/manager/complaints/{t}/status", json={"status": "In Progress", "remark": "on it"}, headers=gm)
    assert mailbox.sent[-1][0] == "student1@college.edu" and "In Progress" in mailbox.sent[-1][1]
    client.post(f"/manager/complaints/{t}/status", json={"status": "Resolved", "remark": "fixed"}, headers=gm)
    assert client.post(f"/manager/complaints/{t}/updates", json={"text": "done"}, headers=gm).status_code == 201

    assert client.post(f"/admin/complaints/{t}/close", json={}, headers=admin).status_code == 400
    client.post(f"/manager/complaints/{t}/close-request", headers=gm)
    r = client.post(f"/admin/complaints/{t}/close", json={}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "Closed"

    steps = [e["new_status"] for e in client.get(f"/complaints/{t}/timeline", headers=h).json() if e["new_status"]]
    assert steps == ["Pending", "Assigned", "In Progress", "Resolved", "Closed"]
    assert client.get("/admin/manager-updates", headers=admin).json()["total"] == 1


def test_pagination_and_filters(client, mailbox):
    _, h = make_student(client, mailbox)
    for i in range(5):
        submit(client, h, {**FAN, "title": f"Fan {i} not working"})
    submit(client, h, {"title": "Ragging in hostel", "description": "seniors troubling", "category": "Ragging"})

    page = client.get("/complaints?page=1&page_size=4", headers=h).json()
    assert page["total"] == 6 and len(page["items"]) == 4
    assert len(client.get("/complaints?page=2&page_size=4", headers=h).json()["items"]) == 2
    assert client.get("/complaints?priority=Critical", headers=h).json()["total"] == 1
    assert client.get("/complaints?category=Infrastructure", headers=h).json()["total"] == 5
    assert client.get("/complaints?status=Assigned&status=Closed", headers=h).json()["total"] == 6
    assert client.get("/complaints?q=fan 3", headers=h).json()["total"] == 1
    assert client.get("/complaints?date_from=2000-01-01&date_to=2000-01-02", headers=h).json()["total"] == 0
    assert client.get("/complaints?close_requested=true", headers=h).json()["total"] == 0
    assert client.get("/complaints?page_size=500", headers=h).status_code == 422


def test_not_found_and_validation_errors(client, mailbox):
    _, h = make_student(client, mailbox)
    r = client.get("/complaints/TKT-NOPE0000", headers=h)
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = client.post("/complaints", json={"title": "x", "description": "y", "category": "Other"}, headers=h)
    assert r.status_code == 422


def test_admin_stats_and_users(client, mailbox):
    _, h = make_student(client, mailbox)
    submit(client, h)
    admin = login(client, "ADMIN001")
    stats = client.get("/admin/stats", headers=admin).json()
    assert stats["counts"]["Total"] == 1 and stats["by_category"] == {"Infrastructure": 1}
    assert len(stats["trend"]) == 30 and stats["trend"][-1]["count"] == 1
    assert client.get("/admin/users?role=student", headers=admin).json()["total"] == 1


def test_cors_only_allows_frontend_origin(client):
    ok = client.options("/health", headers={"Origin": "http://localhost:5173",
                                            "Access-Control-Request-Method": "GET"})
    bad = client.options("/health", headers={"Origin": "http://evil.example",
                                             "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


def test_priority_preview(client, mailbox):
    _, h = make_student(client, mailbox)
    r = client.get("/complaints/priority-preview", params={"title": "ragging", "description": "x"}, headers=h)
    assert r.json() == {"priority": "Critical"}
