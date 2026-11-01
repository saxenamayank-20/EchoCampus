"""Indexes policy PDFs for the policy assistant.

    python scripts/load_sample_policies.py path/to/Handbook.pdf "Student Handbook 2026-27"
        -> indexes your own pdf (e.g. the EchoCampus sample student handbook)
    python scripts/load_sample_policies.py
        -> no file given: makes 3 small SAMPLE policies instead

Run from the repo root (tables must exist, needs GEMINI_API_KEY for the embeddings).
A policy with the same title is skipped, so running it twice is safe.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.ai.llm_client import get_llm
from backend.app.db.session import SessionLocal
from backend.app.services.policy_service import PolicyService
from backend.app.services.storage import get_storage
from backend.app.services.user_service import UserService
from backend.app.utils.pdfgen import make_pdf

BANNER = "SAMPLE POLICY - NOT AN OFFICIAL COLLEGE DOCUMENT. Made for the EchoCampus demo."

SAMPLES = {
    "SAMPLE - Hostel and Anti-Ragging Policy": [
        f"{BANNER}\nHostel and Anti-Ragging Policy (Sample)\n\n"
        "1. Hostel timings. The hostel gate closes at 10:00 pm on weekdays and 11:00 pm on Saturdays and "
        "Sundays. Students returning late must sign the late entry register and inform the warden by phone. "
        "Three late entries in one month lead to a written warning sent to the parents.\n\n"
        "2. Guests. Day visitors are allowed between 9:00 am and 7:00 pm in the visitors room only. "
        "Overnight guests are not allowed in student rooms.\n\n"
        "3. Mess. Breakfast is served from 7:00 to 9:00 am, lunch from 12:30 to 2:30 pm and dinner from "
        "7:30 to 9:30 pm. Complaints about food quality should be raised within 24 hours with the date and meal.",
        f"{BANNER}\n4. Ragging. Ragging in any form is strictly banned on campus and in hostels, as per UGC "
        "regulations. This includes forcing juniors to do tasks, verbal abuse, threats, and online harassment.\n\n"
        "5. How to report ragging. Students can report ragging to the Anti-Ragging Cell (Admin Block, Room 5), "
        "to the hostel warden, through EchoCampus under the Ragging category, or on the national anti-ragging "
        "helpline 1800-180-5522. Reports are kept confidential.\n\n"
        "6. Action. Complaints of ragging are treated as Critical and handled within 24 hours. Proven ragging "
        "can lead to suspension from the hostel, suspension from the college, or expulsion.",
    ],
    "SAMPLE - Examination and Results Policy": [
        f"{BANNER}\nExamination and Results Policy (Sample)\n\n"
        "1. Eligibility. A minimum of 75 percent attendance in each subject is required to sit the end "
        "semester examination. Students with medical reasons may apply for condonation of up to 10 percent "
        "with a medical certificate.\n\n"
        "2. Results. End semester results are published on the student portal within 30 days of the last "
        "examination. If a result is missing on the portal, the student should contact the Examination Cell "
        "within 7 days of publication.\n\n"
        "3. Revaluation. Students can apply for revaluation within 10 days of the result date. The fee is "
        "500 rupees per subject. Revaluation results are announced within 21 days.",
        f"{BANNER}\n4. Timetable clashes. If two examinations are scheduled at the same time for a student, "
        "the student must inform the Examination Cell at least 7 days before the first exam. A separate slot "
        "will be given.\n\n"
        "5. Re-examination. Students who fail a subject can appear in the supplementary examination held in "
        "July. The supplementary exam fee is 750 rupees per subject.",
    ],
    "SAMPLE - Fees and Scholarship Policy": [
        f"{BANNER}\nFees and Scholarship Policy (Sample)\n\n"
        "1. Fee deadlines. Semester fees must be paid by the 15th of the first month of the semester. "
        "A late fee of 100 rupees per day is charged after the deadline, up to a maximum of 2000 rupees.\n\n"
        "2. Receipts. A receipt is generated automatically within 48 hours of an online payment. If no receipt "
        "appears after 48 hours, students should raise a Fee/Finance complaint with the transaction ID.\n\n"
        "3. Refunds. The hostel caution deposit is refunded within 45 days after the student leaves the hostel "
        "and returns the room key. Fee refunds on withdrawal follow the UGC refund rules.\n\n"
        "4. Scholarships. Merit scholarships are credited within 45 days after document verification is "
        "complete. Students whose scholarship is delayed beyond 45 days can raise a Scholarship complaint.",
    ],
}


def main() -> int:
    with SessionLocal() as db:
        admin = UserService(db).get("AD100")
        if not admin:
            print("[POLICIES] no AD100 admin yet, start the backend once (or run scripts/seed.py) first")
            return 1
        service = PolicyService(db, get_llm(), get_storage())
        existing = {d.title for d in service.all_policies()}
        if len(sys.argv) > 1:
            path = sys.argv[1]
            title = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(path))[0]
            if title in existing:
                print(f"[POLICIES] skip (already there): {title}")
                return 0
            with open(path, "rb") as f:
                doc = service.upload(admin, title, os.path.basename(path), f.read())
            print(f"[POLICIES] added: {title} ({doc.pages} pages, {len(doc.chunks)} chunks)")
            return 0
        for title, pages in SAMPLES.items():
            if title in existing:
                print(f"[POLICIES] skip (already there): {title}")
                continue
            doc = service.upload(admin, title, title.replace(" ", "_") + ".pdf", make_pdf(pages))
            print(f"[POLICIES] added: {title} ({doc.pages} pages, {len(doc.chunks)} chunks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
