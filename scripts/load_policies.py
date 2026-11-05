"""Indexes the policy PDFs in data/policies/ for the policy assistant (the RAG sources).

    python scripts/load_policies.py                       # every pdf in data/policies/
    python scripts/load_policies.py some.pdf "Its title"  # one specific pdf

Each pdf goes through the indexing pipeline: read text per page -> chunk -> embed -> store
in policy_chunks. Run from the repo root (tables must exist, needs GEMINI_API_KEY).
A policy with the same title is skipped, so running it twice is safe.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ai.llm_client import get_llm
from backend.app.db.session import SessionLocal
from backend.app.services.policy_service import PolicyService
from backend.app.services.storage import get_storage
from backend.app.services.user_service import UserService

POLICY_DIR = ROOT / "data" / "policies"

# nicer titles for the files we ship, anything else uses its file name
TITLES = {"EchoCampus_Student_Handbook_2026-27.pdf": "Student Handbook 2026-27"}


def main() -> int:
    if len(sys.argv) > 1:
        files = [(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else Path(sys.argv[1]).stem)]
    else:
        files = [(p, TITLES.get(p.name, p.stem)) for p in sorted(POLICY_DIR.glob("*.pdf"))]
    if not files:
        print(f"[POLICIES] no pdfs found in {POLICY_DIR}")
        return 1

    with SessionLocal() as db:
        admin = UserService(db).get("AD100")
        if not admin:
            print("[POLICIES] no AD100 admin yet, start the backend once (or run scripts/seed.py) first")
            return 1
        service = PolicyService(db, get_llm(), get_storage())
        existing = {d.title for d in service.all_policies()}
        for path, title in files:
            if title in existing:
                print(f"[POLICIES] skip (already there): {title}")
                continue
            doc = service.upload(admin, title, path.name, path.read_bytes())
            print(f"[POLICIES] added: {title} ({doc.pages} pages, {len(doc.chunks)} chunks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
