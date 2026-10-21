# Rules for working on my projects

These rules apply to every project and every model. If a project has its own spec file (like UPGRADE_PLAN.md), that file decides the scope, and these rules decide how the work is done.

## Git
- Never push to GitHub. Only make local commits. I push myself.
- Never add AI attribution to commits or PRs:
  - no "Co-Authored-By: Claude/AI" lines
  - no "Generated with ..." footers
  - no mention of AI in commit messages
- Commits must show only me as the author/contributor.
  - Never change git user.name / user.email.
  - Before every commit, check the message has no "Co-Authored-By", "Generated with" or "Claude-Session" lines.
- Never commit things that don't belong in the repo:
  - deployment files (Dockerfile, docker-compose, Render/Vercel configs, CI workflows) unless I ask for them
  - temp scripts, logs, local notes, test output
  - .venv, node_modules, uploads, .env
- Write commit messages in a short, plain style.
- Run the tests (if the project has them) before every commit. Don't commit broken code.

## Code comments
- Write comments like a human developer would: short, casual, lowercase is fine.
  e.g. "# backend url", "# render free plan goes to sleep, so first call can be slow"
- No instruction-style or over-explained comments. Match the style already in the files.
- Docstrings, if needed, stay short and plain, in the same tone as comments.
- Don't rewrite or remove my existing comments unless I ask.

## README
- Plain, first-person tone ("A small app I built to...").
- No emoji on every heading.
- No buzzwords ("beautiful", "robust", "seamless").
- No generic template sections like "Contributing" or "Star this repo".
- Keep it accurate to the real code: tech stack, versions, API routes.
- Keep it scannable: short sections, short lists, no walls of text.
- Don't dump full docs into it. Long details go in a `docs/` folder and get linked.
- Update the README whenever features, setup steps or routes change.
- No localhost or local URLs in the README. If a port matters, say it in plain text ("backend runs on port 8000").
- No links that don't work.
- No deployment section or live link until the project is actually deployed.

### README structure (use this order, skip sections that don't apply)
1. **Name + one line.** What it is, plain words: "A small app I built to..."
2. **Screenshot, GIF or live link.** Right at the top.
3. **Why I built it.** 2–3 lines about the problem it solves.
4. **Features.** Short list of what it actually does today. Nothing planned or fake.
5. **Tech stack.** With versions where they matter.
6. **How it works.** Short explanation of the flow. Add a simple architecture diagram (Mermaid is fine) for bigger projects.
7. **Run it locally:**
   - prerequisites
   - clone the repo
   - create the `.venv`
   - `pip install -r requirements.txt` / `npm install`
   - copy `.env.example` to `.env` (list the variable names only, never values)
   - exact commands to start the backend and the frontend

   Every command must actually work as written.
8. **API routes.** Small table: method, route, what it does. Backend projects only.
9. **Project structure.** Short folder tree, top level only.
10. **Running tests.** The one command.
11. **Challenges / what I learned.** 2–4 honest lines on the hard parts and how I solved them.
12. **Known limitations and what's next.** Honest notes (e.g. "render free plan sleeps, first load is slow").

Small projects only need sections 1, 2, 3, 4, 5 and 7.

### README: don't
- Walls of badges. A single CI badge is fine, but only if CI actually passes.
- "Contributing", "Star this repo", "Acknowledgments" or license sections, unless they're real (a license only if one is actually chosen).
- Emoji headings, buzzwords, a marketing tone.
- A table of contents, unless the README is genuinely long.

## Tech stack
- Frontend is always React + Vite + Tailwind CSS in plain JavaScript (.jsx).
- Never use TypeScript.
- Backend is Python unless I say otherwise.
- Don't add new packages or libraries without telling me first and why.

## Environment and secrets
- Use the project virtual environment (.venv). Never install packages globally.
- Secrets (like DATABASE_URL, API keys) live only in .env, which is gitignored.
- Never commit .env, and never print or paste secret values.
- Keep .env.example updated with placeholder values.
- Keep a single requirements.txt (no separate dev requirements file).

## How I like to work
- When something is broken, first give me a list of the things that need fixing.
  Then we go through them one by one.
- Keep solutions simple and quick. Don't over-engineer.
  If a project spec asks for a bigger structure, follow the spec, but keep each piece inside it simple.
- Before deleting or rewriting things, tell me what will change.
- If something in my request seems wrong or risky, say so before doing it.
