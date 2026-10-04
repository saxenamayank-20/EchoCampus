# College Complaint Portal — Upgrade Plan (for AI coding agent)

## 0. Read this first: rules for the agent

1. **Work one stage at a time.** Finish a stage, make sure the app runs, run the tests, then STOP and summarize what changed, what to test manually, and what the owner must provide next. Do not start the next stage until the owner says so.
2. **Do not remove existing features.** Everything the portal does today must still work after every stage (see Section 2).
3. **Never commit secrets.** All keys, passwords and URLs go in `.env`. Keep `.env.example` updated with placeholder values.
4. **Ask before changing scope.** If something in this plan seems wrong or impossible, explain why and propose an alternative instead of silently doing something else.
5. **Verify library APIs and model names against official docs** (LangGraph, google-genai, SQLAlchemy 2.x, pgvector). Do not guess model names or function signatures.
6. Write clean, typed Python (type hints, docstrings on public functions). Small commits with clear messages, one per logical change.
7. Every stage ends with tests passing (`pytest`).
8. **Free tools only.** Everything must run on free tiers or open-source libraries. Do not add any service that needs payment or a credit card. If something would need payment, stop and ask.
9. **Respect free-tier API limits.** LLM and embedding calls must be throttled, retried with backoff on 429 errors, and never fired in big parallel bursts.

---

## 1. Project context

- Final-year college major project. Owner: Mayank (student, aiming for AI/GenAI Application Engineer + backend roles).
- Goal: upgrade the existing portal (no rebuild from scratch) so it covers a full backend + applied AI roadmap:
  - Phase 1: Python/OOP
  - Phase 2: FastAPI
  - Phase 3: PostgreSQL + Redis
  - Phase 4: RAG + pgvector
  - Phase 5: LangGraph agents + deployment
- Repo: https://github.com/saxenamayank-20/College_Complaint_Portal
- The project must be demo-able in a viva: clear architecture, working features, sensible seed data.
- The owner wants a modern, polished UI. Streamlit is being replaced by a React frontend (Stage 4).
- Deployment (Stage 9) is deferred until Stages 0–8 are done.

---

## 2. Current state (what exists today)

**Stack:** Python, Streamlit (UI), SQLite (raw SQL via `sqlite3`), bcrypt, pandas, python-dotenv, an optional FastAPI layer that the UI does NOT use.

**Files:**
- `main.py` — Streamlit entry, role-based routing
- `app/pages/{auth,student,manager,admin}.py` — dashboards
- `app/components/ui.py` — shared UI helpers
- `database/connection.py` — SQLite connection
- `database/models.py` — all SQL + business logic in one file
- `config/settings.py` — predefined users, category→manager map, keyword priority, password rules, student ID generator
- `api/routes.py` — FastAPI endpoints (no auth)

**Features that must keep working:**
- Roles: student, grievance_manager (4 managers, each owns categories), admin
- Student registration with auto-generated IDs (`ST000101`…), password strength rules, login
- Complaint submission → auto-assign manager by category (`CATEGORY_MANAGER_MAP`) → auto-detected priority (keyword based)
- Critical complaints get a Google Meet link
- Ticket IDs like `TKT-ABC12345`
- Status flow: Pending → Assigned → In Progress → Resolved → Closed
- Manager: view active/resolved complaints, update status with remarks, post updates for admin, request closure
- Admin: view all complaints, users, stats, manager updates; officially close complaints
- Full complaint history/timeline

**Known problems to fix:**
1. Real admin/manager passwords are hardcoded in `config/settings.py` in a PUBLIC repo.
2. API has no authentication; callers pass their own `manager_uid`/`admin_id` in the request body.
3. `STATUS_FLOW` is not enforced; any status can jump to any other.
4. Streamlit talks to the DB directly; the API is unused.
5. `complaints` table duplicates student/manager name & email (denormalized, goes stale).
6. README mentions MySQL connection pool; the code uses SQLite. `generate_student_id` uses MySQL-style SQL (`CAST(... AS UNSIGNED)`).
7. No email validation beyond uniqueness; no email verification.
8. No tests.

---

## 3. Target architecture

```
React frontend      ──HTTP + JWT──>  FastAPI backend  ──>  Neon PostgreSQL (+ pgvector)
                                          │
                                          ├──> Redis (Upstash) — cache + rate limit (optional, app works without it)
                                          ├──> LLM provider (Gemini by default, behind an interface)
                                          └──> SMTP (email OTP + notifications)
```

- **FastAPI is the single source of truth.** The React frontend only talks to the API.
- **Neon PostgreSQL** replaces SQLite. Enable the `vector` extension (pgvector).
- **SQLAlchemy 2.x** ORM + **Alembic** migrations.
- **LLM access goes through one module** (`ai/llm_client.py`) so the provider can be swapped by changing `.env`.

### Target folder structure

```
backend/
  app/
    main.py                 # FastAPI app factory, router registration, startup
    core/
      config.py             # pydantic-settings, reads .env
      security.py           # password hashing (bcrypt), JWT create/verify
      deps.py               # get_db, get_current_user, require_role(...)
    db/
      session.py            # engine + SessionLocal (Neon URL)
      base.py
    models/                 # SQLAlchemy models (one file per table group)
    schemas/                # Pydantic request/response models
    repositories/           # DB access only (no business rules)
    services/               # business rules: auth, complaints, status machine, SLA, notifications
    api/routes/             # auth, complaints, manager, admin, policies, assistant, insights
    ai/
      llm_client.py         # provider abstraction + logging to llm_calls
      triage.py             # Phase 4.1
      embeddings.py
      duplicates.py         # Phase 4.2
      rag.py                # Phase 4.3 (ingest + answer)
      reply_suggest.py      # Phase 4.4
    agents/
      intake_graph.py       # Phase 5 LangGraph intake workflow
      insights.py           # Phase 5 weekly insights job
    jobs/scheduler.py       # APScheduler: SLA check, weekly insights
  alembic/
  tests/
frontend/                   # React + Vite + TypeScript + Tailwind + shadcn/ui
  src/
    api/                    # typed API client (axios/fetch), attaches JWT, handles 401
    auth/                   # auth context, protected routes, role guards
    pages/                  # login, register, verify-otp, student/, manager/, admin/
    components/             # shared UI: status/priority badges, timeline, tables, charts
    lib/
scripts/
  seed_demo_data.py         # ~60 realistic complaints incl. near-duplicates, for demo
docker-compose.yml
.env.example
(Dockerfile/docker-compose/CI come in Stage 9, deferred)
```

---

## 4. Data model (PostgreSQL)

Use enums for role, status, priority. Use foreign keys and indexes.

- **users**: id, user_id (unique, e.g. ST000101/GM001/ADMIN001), name, email (unique), password_hash, role, department, is_verified (bool), is_active, created_at
- **manager_categories**: manager_id FK → users, category (unique). Seeded from the current `CATEGORY_MANAGER_MAP`.
- **email_otps**: id, user_id FK, code_hash, expires_at, attempts, used (bool)
- **complaints**:
  - id, ticket_id (unique), student_id FK, title, description, category, ai_summary
  - priority, priority_source (`keyword` | `ai` | `manual`)
  - status, assigned_to FK
  - student_remarks, manager_remarks, meet_link, close_requested
  - duplicate_of FK nullable, embedding `vector(EMBEDDING_DIM)`
  - sla_due_at, escalated (bool), created_at, updated_at, resolved_at
  - Indexes: (assigned_to, status), (status, created_at), plus an HNSW index on embedding
- **complaint_supporters**: complaint_id FK, student_id FK, created_at (unique pair). This is the "+1 / I have this issue too" table.
- **closure_confirmations**: id, complaint_id FK, requested_by FK (manager), manager_note, student_response (`pending` | `confirmed` | `disputed` | `auto_confirmed`), student_reason, rating (1–5, nullable), due_at, responded_at, admin_decision (`approved` | `sent_back`), admin_note, created_at. One row per close request, so a ticket can go through several rounds.
- **notifications**: id, user_id FK, complaint_id FK nullable, type, message, is_read, created_at (in-portal bell icon).
- **complaint_history**: id, complaint_id FK, changed_by FK, action, old_status, new_status, note, timestamp
- **manager_updates**: id, complaint_id FK, manager_id FK, update_text, created_at
- **attachments**: id, complaint_id FK, original_name, stored_name, mime_type, size_bytes, uploaded_by FK, created_at. Storage backend must be pluggable: local folder now, cloud storage at deployment.
- **policy_documents**: id, title, filename, uploaded_by, created_at
- **policy_chunks**: id, document_id FK, chunk_index, page, content, embedding `vector(EMBEDDING_DIM)`
- **llm_calls**: id, feature (`triage` / `embedding` / `rag` / `reply` / `insights` / `agent`), model, input_tokens, output_tokens, latency_ms, success, error, created_at
- **insight_reports**: id, period_start, period_end, content, created_at

Student/manager names and emails are fetched via joins, not copied into `complaints`. The existing SQLite data is demo data: re-seed instead of migrating, unless the owner asks otherwise.

---

## 5. Stages (do in order, stop after each)

### Stage 0 — Security & hygiene
- Move all seed passwords to `.env` (`ADMIN_SEED_PASSWORD`, `GM001_PASSWORD`…). Remove them from code. Add `.env.example`.
- Make sure `.gitignore` covers `.env`, `*.db`, `__pycache__`, uploads.
- Tell the owner the old passwords were public and must be changed.
- Fix the README tech stack.

**Done when:** no secrets in tracked files; the app still runs.

### Stage 1 — Data layer: Neon + SQLAlchemy + Alembic (roadmap Phase 3)
- Create the folder structure above (backend/frontend split).
- SQLAlchemy 2.x models for Section 4. pgvector columns can be added now or in Stage 6, but via a migration.
- Alembic initial migration. Enable the `vector` extension in a migration.
- `DATABASE_URL` from `.env` (Neon connection string, `sslmode=require`).
- Seed script: admin, 4 managers, manager_categories.
- Student ID generation done safely in Postgres (sequence or a locked query, not "max + 1" race-prone logic).

**Done when:** `alembic upgrade head` works against Neon and the seed runs.

### Stage 2 — OOP services, status machine, tests (roadmap Phase 1)
- Repositories (DB only) and services (rules) for users and complaints.
- Enums for Role, Status, Priority.
- `StatusMachine` with allowed transitions:
  - Assigned → In Progress
  - In Progress → Resolved
  - Resolved → In Progress (reopen)
  - Resolved → Closed (admin only, after close request)
  - Pending → Assigned (system)
- Invalid transitions raise a domain error. Every transition writes `complaint_history`.
- Keep the keyword priority logic as `KeywordPriorityDetector` (still used in Stage 6 as the safety floor).
- pytest: routing by category, keyword priority, every allowed and disallowed transition, ticket ID format. Use a test database (separate Neon branch or a local Postgres in Docker).

**Done when:** tests pass; the business logic has no Streamlit/FastAPI imports.

### Stage 3 — FastAPI backend + auth (roadmap Phase 2)
- Routers: auth, complaints (student), manager, admin. Pydantic schemas for every request/response.
- **JWT auth:**
  - Login returns an access token (about 30 min) containing `sub` (user_id), `role`, `exp`. Use PyJWT. Secret in `.env` (`JWT_SECRET`).
  - `get_current_user` dependency reads the Bearer token.
  - `require_role("admin")`-style dependencies.
  - Remove all `manager_uid`/`admin_id`/`student_id` fields from request bodies; identity comes ONLY from the token.
- **Authorization:**
  - Students see only their own complaints.
  - Managers see/update only complaints in their categories.
  - Only admin closes complaints, views all users, views stats.
- **Email validation:**
  - `EmailStr` format check.
  - Domain allow-list from `.env` (`ALLOWED_EMAIL_DOMAINS`, comma-separated). If empty, allow any domain (dev mode).
  - Registration creates an unverified user and emails a 6-digit OTP (hashed in DB, 10-min expiry, max 5 attempts, resend endpoint). Login is blocked until verified.
  - SMTP settings from `.env`. If SMTP is not configured, log the OTP to the console in dev mode.
- Pagination + filters (status, category, priority, date range) on list endpoints.
- Consistent error format; proper HTTP status codes (401, 403, 404, 409, 422).
- Restrict CORS to the frontend origin from `.env`.
- Email notification to the student on status change, using FastAPI BackgroundTasks.
- Tests with FastAPI TestClient: auth flow, role restrictions, a student cannot read another student's ticket, a manager cannot touch another category.

**Done when:** all features from Section 2 are available through the API with auth; Swagger docs at `/docs` work.

### Stage 4 — Modern React frontend (replaces Streamlit)
- **Stack:** React + Vite + TypeScript + Tailwind CSS + shadcn/ui components, React Router, TanStack Query for API data, Recharts for admin charts, lucide-react icons. All free/open source.
- **Look and feel:** clean, modern SaaS-style dashboard:
  - Sidebar navigation per role, light/dark mode, responsive for mobile.
  - Status/priority badges, toast notifications, loading skeletons, empty states.
  - A visual ticket timeline (reuse the idea of the current Streamlit progress tracker).
- **Auth:**
  - Login, register, OTP verification screens.
  - JWT kept in memory + sessionStorage. On 401, redirect to login.
  - Route guards per role.
- **Student pages:**
  - New complaint form with a live AI suggestion panel (added in Stage 6).
  - My tickets (table + filters), ticket detail with timeline.
  - Policy assistant chat (added in Stage 7).
- **Manager pages:** active/resolved queues with filters, ticket detail (status update, remarks, updates to admin, close request, reply suggestion panel added in Stage 7).
- **Admin pages:**
  - Overview with charts (complaints by category/status/priority, trend over time, SLA breaches).
  - All complaints, users, manager updates, close-request approvals, policy document upload, weekly insights (Stage 8).
- Use the existing Streamlit pages as the feature reference, then delete Streamlit once every feature is covered and the owner confirms.
- Backend CORS allows `FRONTEND_ORIGIN` (Vite dev server, http://localhost:5173).
- The README explains `npm install` / `npm run dev`.

**Done when:** the full student → manager → admin flow works end-to-end in the React app through the API, and Streamlit is removed.

### Stage 5 — Redis, SLA escalation, attachments (roadmap Phase 3)
- **Redis** (`REDIS_URL`, Upstash compatible) behind a small cache interface. If `REDIS_URL` is empty, use an in-memory/no-op fallback so the app still runs.
  - Cache admin stats (60 s TTL; invalidate on complaint changes).
  - Rate limit: complaint submission per student (default 5/hour) and login attempts per IP. Return 429 when exceeded.
- **SLA:**
  - `sla_due_at` set at submission from priority. Hours are configurable in `.env`; defaults: Critical 4, High 48, Medium 72, Low 168.
  - An APScheduler job (every 15 min) plus an admin endpoint to trigger it manually marks overdue complaints `escalated`, writes history, and notifies the admin.
  - Admin dashboard shows the overdue list.
- **Proof attachments (core feature):**
  - Students can attach proof when submitting, and add more later on their ticket.
  - Managers can also attach files in their updates.
  - **Allowed:** images/screenshots (jpg, jpeg, png, webp), PDF, Word (docx).
  - **Limits:** max 5 MB per file and max 5 files per complaint (configurable).
  - **Validation:** check the real file type from its content (magic bytes), not just the extension. Reject everything else, especially executables and archives.
  - **Storage:** save under a random generated name, never the user's filename. Keep the original name only in the DB for display. Store in a local `uploads/` folder for now; cloud storage is decided at deployment time.
  - **Access control:** files are NOT public. They are served only through an authenticated endpoint, and only the owning student, the assigned manager and the admin can view or download them.
  - **Frontend:** drag-and-drop upload with progress, image thumbnails, PDF/DOCX shown as file chips, inline preview for images and PDFs.
  - **Tests:** wrong type rejected, oversize rejected, other students get 403.

**Done when:** stats are cached, rate limits return 429, and overdue complaints get escalated in a test.

### Stage 5b — Student confirmation loop before closing
When a manager requests closure, the student who raised the complaint must confirm it was really fixed before the admin can close it.

- **Flow:**
  1. Manager marks Resolved and requests closure with a short note on what was done.
  2. This creates a `closure_confirmations` row (`pending`, `due_at` = now + `CONFIRMATION_WINDOW_DAYS`, default 3).
  3. The student gets an in-portal notification + email: "Your complaint TKT-… was marked resolved. Was it fixed?"
  4. The student clicks **Yes, resolved** (optional 1–5 rating) or **No, still an issue**. Not resolved requires a reason, and they can attach new proof.
  5. **Confirmed:** the admin sees the close request with a green "Student confirmed" badge and approves closure.
  6. **Disputed:** the ticket goes back to In Progress automatically and the admin and manager are notified. The admin sees the student's reason next to the manager's note and can send a message to the manager in the ticket thread. The manager cannot request closure again without adding a new note.
  7. **No response by `due_at`:** auto-confirm (`auto_confirmed`), clearly labelled for the admin, so tickets never get stuck forever. A reminder goes to the student 1 day before the deadline.
- **Supporters:** students who did +1 on the ticket get notified that it was resolved. Only the original student confirms or disputes. Supporters may add a "still an issue for me" comment, which the admin sees.
- **Admin must never close a ticket while confirmation is `pending`,** except with an explicit override that requires a written reason and is logged in history.
- **Quality metrics on the admin dashboard:**
  - Dispute rate per manager (disputed ÷ close requests).
  - Average student rating per manager and category.
  - "Reopened after closure request" count.
- In-portal notifications: bell icon with unread count; mark as read.
- Use the confirmation reply token in email links only to take the student to the portal (login still required). Never accept a confirm/dispute action from an unauthenticated link.
- **Tests:** confirm path, dispute path (status returns to In Progress), auto-confirm after the deadline, admin blocked while pending, override logged.

**Done when:** a full round (manager request → student dispute → manager fixes → student confirms → admin closes) works end-to-end and shows correctly in the timeline.

### Stage 6 — AI triage + duplicate detection (roadmap Phase 4)
- **`ai/llm_client.py`:**
  - Provider abstraction; default Gemini via the official `google-genai` SDK.
  - Model names from `.env` (`LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`). Verify current model names in the docs.
  - Use free-tier Flash / Flash-Lite models only.
  - Timeouts, retries with exponential backoff on 429, and a simple client-side throttle (`LLM_MAX_RPM`).
  - Cache embeddings: never re-embed text that already has an embedding.
  - Every call logged to `llm_calls` (tokens, latency, success).
- **Triage** (`ai/triage.py`):
  - Input: title + description + student-selected category.
  - The LLM returns JSON validated by Pydantic: `{category, priority, summary, reasoning}`.
  - **Safety floor (mandatory):** final priority = max(AI priority, keyword priority). If the keyword detector says Critical, it stays Critical. The AI can raise priority, never lower it.
  - If the LLM fails or returns invalid JSON, fall back to keyword priority + the student's category and set `priority_source='keyword'`.
  - Show the AI-suggested category to the student before submit (they can accept or keep their own).
  - Managers can manually override priority (`priority_source='manual'`, logged in history).
- **Self-harm/crisis handling:**
  - If the text matches the crisis keywords (suicide, self-harm, mental health), the student immediately sees a supportive message with the campus counsellor contact and the Tele-MANAS helpline (14416), in addition to the Critical routing.
  - Both contact details are configurable in `.env`.
  - Do NOT rely on the LLM alone for this.
- **Duplicate detection** (`ai/duplicates.py`):
  - Embed title + description on submit and store it in `complaints.embedding`.
  - Before final submit, query the nearest OPEN complaints (same category or any) with cosine similarity above `DUPLICATE_THRESHOLD` (default 0.85, configurable). Show the top 3.
  - The student can either support an existing ticket (adds a `complaint_supporters` row, notifies the manager) or submit anyway.
  - Managers see "N students affected". The admin can merge a ticket into another (`duplicate_of`).
- Seed script generates realistic complaints, including near-duplicates, so the demo shows clustering. Embeddings for seed data are created slowly within the rate limit.
- Tests: mock the LLM. Test the safety floor (AI says Low on a ragging complaint → stays Critical), the fallback path, and the duplicate threshold logic.

**Done when:** submissions get AI triage with a working fallback, and duplicates show up in the demo.

### Stage 7 — Policy assistant (RAG) + reply suggestions (roadmap Phase 4)
- **Admin uploads policy PDFs** (`pypdf`):
  - Chunk about 500–800 tokens with overlap. Keep the page number.
  - Embed and store in `policy_chunks`.
  - Re-upload replaces the old chunks for that document.
- **Student "Ask before you complain" chat** (`ai/rag.py`):
  - Retrieve the top-k chunks by vector similarity.
  - The LLM answers ONLY from the retrieved chunks, with citations (document title + page).
  - If the chunks don't contain the answer, it says so clearly and offers a "Raise a complaint" button with the question prefilled.
  - No answer is made up from general knowledge.
- **Manager reply suggestions** (`ai/reply_suggest.py`):
  - On opening a ticket, find similar RESOLVED complaints and their manager remarks.
  - The LLM drafts a reply/next steps.
  - The manager must edit/approve; it is never sent automatically.
- The owner will provide sample policy PDFs. Until then, generate 2–3 clearly labelled SAMPLE policy documents for testing.
- Tests: chunking, the retrieval returns the expected chunk for a known question, the "not found" path.

**Done when:** policy Q&A answers with citations, refuses when the answer isn't in the docs, and reply drafts appear for managers.

### Stage 8 — LangGraph agents (roadmap Phase 5)
- **Intake graph** (`agents/intake_graph.py`): rewrite the submission pipeline as a LangGraph `StateGraph`.
  - Nodes: `classify` (Stage 6 triage) → `check_duplicates` → conditional edge: Critical → `escalate` (meet link + admin alert) → `route` (assign manager, set SLA) → `notify`.
  - State is a typed dict holding the complaint data and each node's result.
  - Errors in AI nodes fall back to the non-AI path (never block a submission).
  - The existing submit endpoint calls the graph.
- **Human-in-the-loop closure:** move the Stage 5b closure flow into a LangGraph graph with two pause points: `await_student_confirmation` (resumed by the student's answer or the auto-confirm deadline), then `await_admin_approval` (resumed by the admin). A dispute routes back to the manager. Business rules stay the same as Stage 5b. Use a Postgres checkpointer if available; verify in the LangGraph docs.
- **Weekly insights** (`agents/insights.py`):
  - A scheduled job (and a manual admin button) gathers last week's stats via SQL: counts by category, week-over-week change, SLA breaches, top duplicate clusters.
  - The LLM writes a short report (max ~8 lines) using ONLY those numbers. Stored in `insight_reports` and shown on the admin dashboard.
- Export a diagram of the intake graph (LangGraph can render Mermaid) for the project report.

**Done when:** submissions run through the graph, closure approval pauses/resumes, and the admin sees the weekly report.

### Stage 9 — Deployment (DEFERRED: do NOT start until the owner asks)
Planned for later, after Stages 0–8 are done: Docker + docker-compose, GitHub Actions CI (ruff + pytest), free hosting for the backend and the React frontend, cloud storage for attachments, and an admin "AI usage" page built from `llm_calls`.

The `llm_calls` logging itself is already built in Stage 6.

---

## 6. Environment variables (`.env.example`)

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
JWT_SECRET=change-me
JWT_EXPIRE_MINUTES=30
ALLOWED_EMAIL_DOMAINS=
FRONTEND_ORIGIN=http://localhost:5173
VITE_API_BASE_URL=http://localhost:8000   # in frontend/.env
ADMIN_SEED_PASSWORD=
GM001_PASSWORD=
GM002_PASSWORD=
GM003_PASSWORD=
GM004_PASSWORD=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
REDIS_URL=
RATE_LIMIT_COMPLAINTS_PER_HOUR=5
SLA_HOURS_CRITICAL=4
SLA_HOURS_HIGH=48
SLA_HOURS_MEDIUM=72
SLA_HOURS_LOW=168
LLM_PROVIDER=gemini
GEMINI_API_KEY=
LLM_MODEL=
EMBEDDING_MODEL=
EMBEDDING_DIM=
DUPLICATE_THRESHOLD=0.85
LLM_MAX_RPM=8
CONFIRMATION_WINDOW_DAYS=3
MAX_UPLOAD_MB=5
MAX_FILES_PER_COMPLAINT=5
COUNSELLOR_CONTACT=
CRISIS_HELPLINE=Tele-MANAS 14416
```

---

## 7. Roadmap coverage (for the project report)

| Roadmap phase | Covered by |
|---|---|
| Phase 1: Python / OOP | Stage 2: services, repositories, enums, status machine, pytest |
| Phase 2: FastAPI | Stage 3–4: full REST API, JWT, role-based access, OTP email verification, background tasks, React frontend consuming the API |
| Phase 3: PostgreSQL / Redis | Stage 1, 5, 5b: Neon + SQLAlchemy + Alembic, indexes, SLA escalation, Redis cache + rate limiting, student confirmation loop + manager quality metrics |
| Phase 4: RAG / pgvector | Stage 6–7: AI triage with safety floor, embedding-based duplicate detection, policy RAG with citations, reply suggestions |
| Phase 5: Agents / deployment | Stage 8: LangGraph intake graph, human-in-the-loop closure, insights agent. Stage 9 (deployment) later |

---

## 8. Inputs the owner must provide

- Neon connection string
- Gemini API key (free, from Google AI Studio)
- College email domain(s)
- SMTP credentials (Gmail app password works)
- Upstash Redis URL (optional)
- Real or sample policy PDFs
- New seed passwords
