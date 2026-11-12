# EchoCampus API

All routes of the FastAPI backend, generated from the app itself. Interactive docs (Swagger) are at `/docs` on the running backend.

Every route except login/register/health needs `Authorization: Bearer <token>`. Errors always look like
`{"error": {"code": "...", "message": "..."}}` (401 not logged in, 403 not allowed, 404 not found,
409 conflict or wrong status move, 413/415 bad file, 422 bad input, 429 rate limited, 503 AI unavailable).

## Auth

| Method | Route | What it does |
|---|---|---|
| POST | `/auth/login` | log in with user ID + password, returns a 30 min JWT |
| POST | `/auth/change-password` | change your own password (needs the current one, same rules as register) |
| GET | `/auth/me` | the logged-in user |
| POST | `/auth/register` | creates an unverified student and emails a 6 digit code. the student id comes after verifying |
| POST | `/auth/resend-otp` | send a new 6 digit code to that email (old ones stop working) |
| POST | `/auth/verify-otp` | check the email + code, returns the new student id (also mailed), then the student can log in |

## Complaints

| Method | Route | What it does |
|---|---|---|
| GET | `/complaints` | students get their own, managers their assigned ones, admin gets everything |
| POST | `/complaints` | submit a complaint (student, max 5 per hour) |
| POST | `/complaints/preview` | before submit: ai category + priority, crisis help, and similar open complaints |
| GET | `/complaints/priority-preview` | live hint on the new complaint form |
| GET | `/complaints/supporting` | complaints this student said "I have this issue too" on |
| GET | `/complaints/{ticket_id}` | one complaint (owner, supporter, assigned manager or admin). supporters don't see who filed it, staff see the supporters list |
| POST | `/complaints/{ticket_id}/confirm` | student answers: fixed (with an optional 1-5 rating) or not fixed (reason needed) |
| POST | `/complaints/{ticket_id}/support` | "I have this issue too" |
| POST | `/complaints/{ticket_id}/supporter-comment` | a supporter says it's still a problem for them |
| GET | `/complaints/{ticket_id}/timeline` | full history of the complaint |

## Attachments

| Method | Route | What it does |
|---|---|---|
| GET | `/attachments/{attachment_id}` | inline = open in the browser (preview), download=true = save as file |
| GET | `/complaints/{ticket_id}/attachments` | list proof files |
| POST | `/complaints/{ticket_id}/attachments` | one file per request, so the frontend can show progress for each |

## Manager

| Method | Route | What it does |
|---|---|---|
| POST | `/manager/complaints/{ticket_id}/close-request` | ask the student to confirm the fix (note required) |
| POST | `/manager/complaints/{ticket_id}/priority` | manager overrides the ai/keyword priority (saved as 'manual') |
| POST | `/manager/complaints/{ticket_id}/reply-suggestion` | an ai draft based on similar fixed complaints. nothing is saved or sent: the manager edits it |
| POST | `/manager/complaints/{ticket_id}/status` | change status / remark (status machine checked, student emailed) |
| GET | `/manager/complaints/{ticket_id}/status-options` | current status first, then the moves the status machine allows |
| POST | `/manager/complaints/{ticket_id}/updates` | progress note for the admin |

## Admin

| Method | Route | What it does |
|---|---|---|
| POST | `/admin/complaints/{ticket_id}/close` | close after the student confirmed (override needs a reason) |
| GET | `/admin/complaints/{ticket_id}/closure-state` | where the closure graph is paused: await_student, await_admin or none |
| POST | `/admin/complaints/{ticket_id}/merge` | ticket_id is a duplicate: close it and add its student as a supporter of `into` |
| POST | `/admin/complaints/{ticket_id}/message` | message to the assigned manager |
| GET | `/admin/insights` | the latest weekly reports, newest first |
| POST | `/admin/insights/run` | write this week's report now (the scheduler also does it every monday) |
| GET | `/admin/ai-usage` | ai calls, failures, tokens and speed per feature (`?days=30`) |
| GET | `/admin/manager-updates` | managers' progress notes, paged |
| GET | `/admin/quality` | dispute rate and student ratings per manager and category |
| POST | `/admin/sla/run` | same job the scheduler runs every 15 minutes, on demand |
| GET | `/admin/stats` | card numbers + chart data for the overview (cached 60 s) |
| GET | `/admin/users` | all users, paged, filter by role |

## Policies

| Method | Route | What it does |
|---|---|---|
| GET | `/admin/policies` | uploaded policy PDFs |
| POST | `/admin/policies` | upload a policy PDF (read, chunk, embed, store) |
| DELETE | `/admin/policies/{doc_id}` | delete a policy and its chunks |
| PUT | `/admin/policies/{doc_id}` | re-upload: old chunks are replaced by the new pdf's |
| POST | `/assistant/ask` | answers only from the uploaded policies, with page citations |

## Notifications

| Method | Route | What it does |
|---|---|---|
| GET | `/notifications` | my bell notifications + unread count |
| POST | `/notifications/read-all` | mark all as read |
| POST | `/notifications/{notification_id}/read` | mark one as read |

## Meta

| Method | Route | What it does |
|---|---|---|
| GET | `/health` | is the backend up |
| GET | `/meta/categories` | complaint categories |
