# StudySpace

A collaborative study platform: groups, chat, notes, files, projects and tasks
in one connected workspace. This repository contains the **MVP** described in
`TASK_PLAN.md`, built against the supplied product, architecture, design and
rulebook specifications.

The full specifications are the PDFs in `uploads/`:
`product details.pdf` (requirements), `architecture.pdf` (technical design),
`design.pdf` (UX/UI) and `agent rule book.pdf` (engineering guardrails).

## Layout

```
studyspace/
├── apps/
│   ├── api/                 FastAPI application
│   │   ├── app/
│   │   │   ├── core/        config, security, database, errors, logging, rate limits
│   │   │   ├── models/      SQLAlchemy models by domain
│   │   │   ├── schemas/     Pydantic request/response schemas
│   │   │   ├── services/    business rules (permissions, auth, groups, chat, content, projects, storage)
│   │   │   ├── api/v1/      thin routers
│   │   │   └── main.py      application factory
│   │   ├── alembic/         migrations
│   │   └── tests/           pytest suite (37 tests)
│   └── web/                 Next.js application
│       └── src/
│           ├── app/         routes (App Router)
│           ├── components/  shell and panel components
│           └── lib/         API client, auth context, formatting
└── var/                     SQLite database and uploaded file blobs (git-ignored)
```

## Running it

### 1. API

```bash
cd apps/api
python3 -m venv ../../.venv && ../../.venv/bin/pip install -e ".[dev]"
cp ../../.env.example ../../.env      # then set a real JWT_SECRET
../../.venv/bin/alembic upgrade head   # create the schema
../../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API refuses to start without `JWT_SECRET`. Generate one with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Health check: `curl http://localhost:8000/health`
Interactive docs (non-production): `http://localhost:8000/docs`

### 2. Web

```bash
cd apps/web
npm install
npm run dev        # http://localhost:3000
```

The web app proxies `/api/*` to the API through a Next.js rewrite, so browser
code only ever calls its own origin. Set `API_ORIGIN` if FastAPI runs
somewhere other than `http://127.0.0.1:8000`.

## Verifying a change

```bash
# API
cd apps/api
../../.venv/bin/python -m pytest          # 37 tests
../../.venv/bin/ruff check .              # lint
../../.venv/bin/mypy app                  # type check

# Web
cd apps/web
npx tsc --noEmit                          # type check
npm run build                             # production build
```

## Architecture notes

- **Layering.** Routers validate and delegate; services hold business rules;
  SQLAlchemy models own persistence. No business logic lives in a route
  handler.
- **Authorisation.** Every protected operation goes through
  `app/services/permissions.py`. The frontend hides controls for convenience
  only — the backend is authoritative.
- **Authentication.** bcrypt password hashing, short-lived JWT access tokens
  and single-use refresh tokens that are rotated and stored only as SHA-256
  hashes.
- **Storage.** File bytes go to a local directory through a
  `StorageBackend` protocol, so an S3-compatible adapter can replace it
  without touching domain code.
- **Timestamps.** Stored and returned as UTC through one column type, so
  SQLite and PostgreSQL behave identically.
- **Errors.** Every failure returns
  `{"error": {"code": "...", "message": "..."}}`. Stack traces and internal
  details are logged, never returned.

## API surface

All routes are under `/api/v1`.

| Area | Endpoints |
| --- | --- |
| Auth | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` |
| Users | `GET /users/me`, `PATCH /users/me` |
| Groups | `POST /groups`, `GET /groups`, `GET /groups/discover`, `POST /groups/join`, `GET/PATCH/DELETE /groups/{id}`, `POST /groups/{id}/leave`, `GET /groups/{id}/members`, `GET /groups/{id}/notes`, `GET /groups/{id}/files` |
| Chat | `GET/POST /groups/{id}/conversations`, `GET/POST /conversations/{id}/messages`, `POST /conversations/{id}/read`, `PATCH/DELETE /messages/{id}` |
| Notes | `GET/POST /notes`, `GET/PATCH/DELETE /notes/{id}` |
| Files | `POST /files`, `GET /files`, `GET /files/{id}` (download), `DELETE /files/{id}` |
| Projects | `GET/POST /groups/{id}/projects`, `GET/PATCH/DELETE /projects/{id}`, `GET/POST /projects/{id}/tasks`, `GET /projects/{id}/board` |
| Tasks | `PATCH /tasks/{id}`, `POST /tasks/{id}/move`, `DELETE /tasks/{id}` |

Success responses return the resource directly; failures use the error
envelope above. Collections are paginated with `limit` (1–100) and `offset`.

## Known limitations

These are deliberate MVP trade-offs, not defects:

1. **Realtime is polling.** Chat refreshes every 5 seconds. WebSockets,
   presence and typing indicators are deferred.
2. **Session storage.** The MVP keeps tokens in `localStorage` so a page
   refresh stays signed in. Moving to httpOnly cookies is the first hardening
   step after the gate.
3. **SQLite for development.** The schema is PostgreSQL-compatible and
   migrations are Alembic-based, but SQLite has no concurrency testing here.
4. **Rate limiting is in-process.** It protects a single instance. Redis is
   required before running more than one API process.
5. **No object storage.** Files live on the local disk behind the storage
   interface; S3-compatible storage is deferred.
6. **No email.** Registration does not verify email addresses and there is no
   password reset.
7. **Global search is not implemented.** The top-bar control is present but
   disabled rather than pretending to work.
8. **Communities, repositories, notifications and analytics are out of MVP
   scope** and are listed in the deferred roadmap in `TASK_PLAN.md`.

## Demo data

Two seeded accounts exist in the local development database used for the
end-to-end walkthrough: `aryan@studyspace.dev` and `rahul@studyspace.dev`,
both with password `password123`. They share the group "Machine Learning
Study Group". Remove `var/studyspace.db` and re-run the migration for a clean
database.
