# StudySpace — Agent-Friendly Build Plan

This is the active implementation plan for this repository. It compresses the
supplied task-book PDF into milestones that can be completed and verified one
at a time, and it is updated to match reality at the end of each milestone.

## Working objective

Build a coherent MVP website for StudySpace: users can register, sign in,
manage a profile, create or join groups, chat, manage notes and files, create
a project, and manage basic tasks.

Advanced features — collaborative cursors, voice, repositories, code
execution, issues, pull requests, OpenSearch, analytics and AI — are
explicitly deferred until the MVP is stable.

## Non-negotiable limits

- Work on one milestone at a time.
- Inspect existing files before editing them.
- Do not create a new file when an existing module can reasonably hold the code.
- Keep the MVP implementation within approximately 35 application source files,
  excluding generated dependencies, migrations and tests.
- Every new endpoint must have a working user flow or a focused test.
- Do not create placeholder endpoints that claim to work.
- Do not add Redis, Celery, S3, WebSockets, rich-text collaboration, Monaco or
  search infrastructure before the MVP gate.
- Use one database access layer and one authentication system.
- Keep business logic in services; keep route handlers thin.
- Stop after verification and report the milestone before moving forward.

## Technology boundary

| Layer | Choice |
| --- | --- |
| Web | Next.js, React, TypeScript, one global stylesheet |
| API | FastAPI, Python, SQLAlchemy, Pydantic |
| Dev database | SQLite (schema stays PostgreSQL-compatible) |
| Prod database | PostgreSQL |
| Auth | bcrypt hashing + short-lived JWT access tokens + rotating refresh tokens |
| Files | Local storage behind a storage service interface (S3 deferred) |
| Realtime | HTTP polling (WebSockets deferred) |

---

## Milestone 0 — Baseline and cleanup — COMPLETED

- Repository tree confirmed: `apps/api` (FastAPI) and `apps/web` (Next.js).
- `.env.example`, `README.md` and this plan are accurate and committed.
- Temporary tooling removed; generated artefacts covered by `.gitignore`.

**Gate passed:** a new agent can find the web app, the API app, the run
commands and the next milestone in under five minutes.

## Milestone 1 — Working application shell — COMPLETED

- Responsive top bar, sidebar, main content area and mobile bottom navigation.
- Design tokens for colour, spacing, radius, typography, borders, shadows and
  focus states in `apps/web/src/app/globals.css`.
- Reusable primitives, added only where used more than once: `Button`,
  `Input`, `Textarea`, `Select`, `Card`, `Avatar`, `Badge`, `EmptyState`,
  `SkeletonList`, `Alert`, `Modal`, `ToastRegion`, `Tabs`.
- Routes: landing, login, register and the protected app shell.

**Gate passed:** the shell renders on desktop, tablet and mobile; keyboard
focus is visible; every page shares one visual system.

## Milestone 2 — API foundation and database — COMPLETED

- Settings, database session, SQLAlchemy base, Alembic migration entry point,
  error handling, CORS and `/api/v1` versioning.
- `User`, `Profile` and persisted refresh-token sessions.
- Endpoints: `/health`, `/auth/register`, `/auth/login`, `/auth/refresh`,
  `/auth/logout`, `/users/me`.
- 37 focused API tests covering health, registration, login, protected access,
  invalid credentials, duplicate email and refresh-token replay.

**Gate passed:** the API starts from a clean environment and all
authentication tests pass.

## Milestone 3 — Authentication and profile UX — COMPLETED

- Login and register forms connected to the API with field-level errors.
- Session persisted for the MVP; the dashboard is protected and expired
  access tokens refresh transparently.
- Profile view and edit for name, username, bio, institution, program, year,
  skills and interests.
- Loading, empty, validation and error states on every route.

**Gate passed:** a new user can register, sign in, refresh the page, view the
dashboard, edit the profile and sign out.

## Milestone 4 — Groups and chat — COMPLETED

- Groups, memberships, roles (OWNER / ADMIN / MEMBER), create, discover,
  join-by-code and leave flows, plus a group workspace page.
- Conversations and messages scoped to a group; every group opens with a
  General channel.
- Message creation, paginated listing, edit, delete and an unread watermark.
- Realtime is refresh/polling; WebSockets are not used.

**Gate passed:** two test users can join the same group and exchange messages
through the UI.

## Milestone 5 — Notes and files — COMPLETED

- Personal and group notes with title, body, owner and updated time.
- Create, edit, list, view, search and delete flows.
- File metadata, upload, download, list and delete through the local storage
  adapter; downloads are always served as attachments.
- Ownership and group membership enforced in the API, not just the UI.

**Gate passed:** a user can create a note and upload/download a real file
inside a group; unauthorised access is rejected.

## Milestone 6 — Projects and tasks — COMPLETED

- Projects belong to a group with name, description, status and deadline.
- Tasks carry title, description, assignee, priority, status and deadline.
- List and board views with the four statuses: TODO, IN_PROGRESS, REVIEW, DONE.
- Create, edit, assign, move and delete flows with backend permission checks.

**Gate passed:** a group can create a project, add tasks, assign a task and
move it across the board.

## Milestone 7 — MVP hardening and release check — COMPLETED

- Regression test covering register → group → chat → note → file → project →
  task.
- Responsive and keyboard checks built into the shell; visible focus states,
  semantic controls, labels and ARIA where needed.
- Rate limiting on authentication and uploads; structured error envelopes and
  request logging with correlation ids.
- README, `.env.example` and this file updated to match reality.
- Lint, type check, Python checks, API tests and the web build all run clean.

**Gate passed:** the MVP works from a clean setup, no critical test or build
failures remain, and known limitations are documented in the README.

---

## Deferred roadmap

Only after Milestone 7 passes, each in a separate bounded effort:

1. Communities and notifications.
2. WebSocket realtime, presence and typing.
3. Collaborative documents using Yjs.
4. Repository, code editor, issues and pull requests.
5. Search, analytics, background workers, object storage and production
   deployment.

## Agent completion report

At the end of each milestone, report: milestone and status
(`IN_PROGRESS` / `BLOCKED` / `COMPLETED`), files changed, the user flow
completed, API/database changes, tests and commands run, known limitations,
and the exact next milestone.

Never report `COMPLETED` when the gate has not passed.
