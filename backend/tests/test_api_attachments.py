import io
import zipfile
from pathlib import Path

from backend.app.core.config import settings
from backend.tests.conftest import login, make_student

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
PDF = b"%PDF-1.7\n" + b"x" * 100
EXE = b"MZ\x90\x00" + b"\x00" * 100
FAN = {"title": "Fan not working", "description": "room 12 fan is broken", "category": "Infrastructure"}


def docx_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


def zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("virus.exe", "MZ")
    return buf.getvalue()


def setup_ticket(client, mailbox):
    _, h = make_student(client, mailbox, "owner@college.edu")
    t = client.post("/complaints", json=FAN, headers=h).json()["ticket_id"]
    return t, h


def upload(client, t, h, name, data):
    return client.post(f"/complaints/{t}/attachments", files={"file": (name, data)}, headers=h)


def test_upload_list_and_download(client, mailbox):
    t, h = setup_ticket(client, mailbox)
    r = upload(client, t, h, "proof.png", PNG)
    assert r.status_code == 201 and r.json()["mime_type"] == "image/png"

    files = client.get(f"/complaints/{t}/attachments", headers=h).json()
    assert [f["original_name"] for f in files] == ["proof.png"]

    r = client.get(f"/attachments/{files[0]['id']}", headers=h)
    assert r.status_code == 200 and r.content == PNG
    assert r.headers["content-type"] == "image/png"
    assert r.headers["content-disposition"].startswith("inline")


def test_pdf_and_docx_allowed(client, mailbox):
    t, h = setup_ticket(client, mailbox)
    assert upload(client, t, h, "notice.pdf", PDF).status_code == 201
    r = upload(client, t, h, "letter.docx", docx_bytes())
    assert r.status_code == 201 and r.json()["mime_type"].endswith("wordprocessingml.document")


def test_wrong_types_rejected(client, mailbox):
    t, h = setup_ticket(client, mailbox)
    for name, data in [("setup.exe", EXE), ("photo.png", EXE),          # exe renamed to .png
                       ("notes.txt", b"hello"), ("stuff.zip", zip_bytes()),
                       ("fake.docx", zip_bytes())]:                       # zip renamed to .docx
        r = upload(client, t, h, name, data)
        assert r.status_code == 415, name
        assert r.json()["error"]["code"] == "unsupported_type"


def test_oversize_rejected(client, mailbox, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    t, h = setup_ticket(client, mailbox)
    r = upload(client, t, h, "big.png", PNG + b"\x00" * (1024 * 1024))
    assert r.status_code == 413


def test_max_files_per_complaint(client, mailbox):
    t, h = setup_ticket(client, mailbox)
    for i in range(settings.max_files_per_complaint):
        assert upload(client, t, h, f"p{i}.png", PNG).status_code == 201
    assert upload(client, t, h, "one-more.png", PNG).status_code == 422


def test_other_student_gets_403(client, mailbox):
    t, h = setup_ticket(client, mailbox)
    file_id = upload(client, t, h, "proof.png", PNG).json()["id"]
    _, other = make_student(client, mailbox, "other@college.edu")
    assert client.get(f"/attachments/{file_id}", headers=other).status_code == 403
    assert client.get(f"/complaints/{t}/attachments", headers=other).status_code == 403
    assert upload(client, t, other, "x.png", PNG).status_code == 403


def test_manager_and_admin_access(client, mailbox):
    t, h = setup_ticket(client, mailbox)
    file_id = upload(client, t, h, "proof.png", PNG).json()["id"]
    assert client.get(f"/attachments/{file_id}", headers=login(client, "GM002")).status_code == 200  # assigned
    assert client.get(f"/attachments/{file_id}", headers=login(client, "GM001")).status_code == 403  # not theirs
    assert client.get(f"/attachments/{file_id}", headers=login(client, "ADMIN001")).status_code == 200
    # the assigned manager can add proof too
    r = upload(client, t, login(client, "GM002"), "fixed.jpg", b"\xff\xd8\xff" + b"\x00" * 50)
    assert r.status_code == 201 and r.json()["uploader_role"] == "grievance_manager"


def test_no_token_401(client, mailbox):
    t, h = setup_ticket(client, mailbox)
    file_id = upload(client, t, h, "proof.png", PNG).json()["id"]
    assert client.get(f"/attachments/{file_id}").status_code == 401


def test_saved_under_random_name(client, mailbox):
    t, h = setup_ticket(client, mailbox)
    upload(client, t, h, "../../etc/passwd.png", PNG)
    saved = list(Path(settings.upload_dir).iterdir())
    assert len(saved) == 1
    assert saved[0].name != "passwd.png" and len(saved[0].stem) == 32 and saved[0].suffix == ".png"
    assert client.get(f"/complaints/{t}/attachments", headers=h).json()[0]["original_name"] == "passwd.png"
