import pytest

from backend.app.ai.chunking import chunk_pages
from backend.app.ai.pdf import extract_pages
from backend.app.core.config import settings
from backend.app.utils.pdfgen import make_pdf
from backend.tests.conftest import login, make_student

HOSTEL = make_pdf(["Hostel gate closes at 10 pm every night. Late entry needs warden permission.",
                   "Ragging is strictly banned. Report ragging to the anti ragging cell in room 5."])
FEES = make_pdf(["Late fee is 100 rupees per day after the fee deadline, up to 2000 rupees."])


# ── pdf + chunking ───────────────────────────────────────────────────────────
def test_pdf_pages_are_read_in_order():
    assert extract_pages(HOSTEL) == ["Hostel gate closes at 10 pm every night. Late entry needs warden permission.",
                                     "Ragging is strictly banned. Report ragging to the anti ragging cell in room 5."]


def test_chunks_keep_page_numbers_and_overlap():
    long = " ".join(f"w{i}" for i in range(1000))
    chunks = chunk_pages(["short page", long])
    assert [c.page for c in chunks] == [1, 2, 2, 2]
    assert [len(c.text.split()) for c in chunks[1:]] == [450, 450, 220]
    assert chunks[1].text.split()[-60:] == chunks[2].text.split()[:60]       # 60 word overlap


def test_unreadable_pdf_gives_no_pages():
    assert extract_pages(b"%PDF-1.4 broken") == []


# ── admin uploads ────────────────────────────────────────────────────────────
def upload(client, headers, title, data, name="p.pdf"):
    return client.post("/admin/policies", data={"title": title}, files={"file": (name, data)}, headers=headers)


@pytest.fixture
def admin(ai_client):
    return login(ai_client, "AD100")


def test_upload_list_replace_delete(ai_client, admin):
    r = upload(ai_client, admin, "Hostel Policy", HOSTEL)
    assert r.status_code == 201 and r.json()["pages"] == 2 and r.json()["chunks"] == 2
    doc_id = r.json()["id"]
    assert [p["title"] for p in ai_client.get("/admin/policies", headers=admin).json()] == ["Hostel Policy"]

    r = ai_client.put(f"/admin/policies/{doc_id}", files={"file": ("v2.pdf", FEES)}, headers=admin)
    assert r.status_code == 200 and r.json()["pages"] == 1 and r.json()["chunks"] == 1    # old chunks gone

    assert ai_client.delete(f"/admin/policies/{doc_id}", headers=admin).status_code == 200
    assert ai_client.get("/admin/policies", headers=admin).json() == []


def test_only_pdfs_and_only_admin(ai_client, admin, mailbox):
    assert upload(ai_client, admin, "x", b"\x89PNG\r\n\x1a\n" + b"0" * 50).status_code == 415
    _, student = make_student(ai_client, mailbox)
    assert upload(ai_client, student, "x", HOSTEL).status_code == 403
    assert upload(ai_client, login(ai_client, "GM101"), "x", HOSTEL).status_code == 403


def test_upload_needs_ai_for_embeddings(ai_client, admin, fake_llm):
    fake_llm.fail = True
    assert upload(ai_client, admin, "Hostel", HOSTEL).status_code == 503
    assert ai_client.get("/admin/policies", headers=admin).json() == []          # nothing half-saved


# ── assistant ────────────────────────────────────────────────────────────────
@pytest.fixture
def ask(ai_client, admin, mailbox, monkeypatch):
    monkeypatch.setattr(settings, "rag_min_similarity", 0.2)    # the fake word-vectors are less precise
    upload(ai_client, admin, "Hostel Policy", HOSTEL)
    upload(ai_client, admin, "Fee Policy", FEES)
    _, student = make_student(ai_client, mailbox)
    return lambda q: ai_client.post("/assistant/ask", json={"question": q}, headers=student)


def cite_source_with(word):
    """fake model: answers from whichever numbered source mentions `word`"""
    def answer(prompt):
        for line in prompt.split("\n"):
            if line.startswith("[") and word in line.lower():
                return {"found": True, "answer": line.split(") ", 1)[1], "citations": [int(line[1])]}
        return {"found": False, "answer": "", "citations": []}
    return answer


def test_answer_comes_from_the_right_page(ask, fake_llm):
    fake_llm.answers["rag"] = cite_source_with("ragging")
    r = ask("Where do I report ragging?").json()
    assert r["answered"] and "anti ragging cell" in r["answer"]
    assert r["sources"][0]["document"] == "Hostel Policy" and r["sources"][0]["page"] == 2


def test_retrieval_puts_the_relevant_chunk_first(ask, fake_llm):
    fake_llm.answers["rag"] = cite_source_with("late fee")
    ask("What is the late fee per day after the deadline?")
    first_source = fake_llm.prompts[-1].split("Sources:")[1].strip().split("\n")[0]
    assert first_source.startswith("[1] (Fee Policy, page 1)")


def test_nothing_relevant_means_not_found_without_asking_the_model(ask, fake_llm):
    fake_llm.answers["rag"] = cite_source_with("x")
    r = ask("Who won the football world cup in 2022?").json()
    assert not r["answered"] and r["suggested_title"].startswith("Who won")
    assert fake_llm.prompts == []          # the model was never asked, so it can't guess


def test_model_says_not_in_sources(ask, fake_llm):
    fake_llm.answers["rag"] = {"found": False, "answer": "", "citations": []}
    r = ask("What time does the hostel gate close for girls on Sunday?").json()
    assert not r["answered"] and r["sources"] == []


def test_answer_without_citation_is_not_trusted(ask, fake_llm):
    fake_llm.answers["rag"] = {"found": True, "answer": "Probably 11 pm.", "citations": [9]}   # source 9 doesn't exist
    assert not ask("When does the hostel gate close?").json()["answered"]


def test_assistant_down_is_503(ask, fake_llm):
    fake_llm.fail = True
    assert ask("When does the hostel gate close?").status_code == 503


# ── reply suggestions ────────────────────────────────────────────────────────
def test_reply_draft_uses_past_fixes_and_changes_nothing(ai_client, mailbox, fake_llm):
    _, h = make_student(ai_client, mailbox)
    gm = login(ai_client, "GM102")
    fan = {"title": "Fan broken in room 12", "description": "ceiling fan in room 12 is broken", "category": "Infrastructure"}
    old = ai_client.post("/complaints", json=fan, headers=h).json()["ticket_id"]
    ai_client.post(f"/manager/complaints/{old}/status", json={"status": "In Progress"}, headers=gm)
    ai_client.post(f"/manager/complaints/{old}/status", json={"status": "Resolved", "remark": "Electrician replaced the capacitor"}, headers=gm)
    new = ai_client.post("/complaints", json={**fan, "title": "Fan broken in room 14",
                                              "description": "ceiling fan in room 14 is broken"}, headers=h).json()["ticket_id"]

    fake_llm.answers["reply"] = {"draft": "We'll send an electrician today.", "steps": ["Check capacitor", "Replace if needed"]}
    r = ai_client.post(f"/manager/complaints/{new}/reply-suggestion", headers=gm).json()
    assert r["draft"] == "We'll send an electrician today." and len(r["steps"]) == 2
    assert [p["ticket_id"] for p in r["based_on"]] == [old]
    assert "Electrician replaced the capacitor" in fake_llm.prompts[-1]
    c = ai_client.get(f"/complaints/{new}", headers=gm).json()
    assert c["manager_remarks"] is None and c["status"] == "Assigned"           # never saved or sent


def test_reply_draft_only_for_the_assigned_manager(ai_client, mailbox, fake_llm):
    _, h = make_student(ai_client, mailbox)
    t = ai_client.post("/complaints", json={"title": "Fan broken", "description": "room 5 fan", "category": "Infrastructure"},
                       headers=h).json()["ticket_id"]
    fake_llm.answers["reply"] = {"draft": "ok", "steps": []}
    assert ai_client.post(f"/manager/complaints/{t}/reply-suggestion", headers=login(ai_client, "GM101")).status_code == 403
    assert ai_client.post(f"/manager/complaints/{t}/reply-suggestion", headers=h).status_code == 403
