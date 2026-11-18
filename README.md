# Mimre

*Mimre* (Norwegian: "to reminisce") is a personal app for remembering things about the people you know: their kids, birthdays, where they live and work, their dog's name.

- **Frontend:** React + TypeScript + Tailwind CSS (Vite), TanStack Query, i18next (Norwegian default, English available)
- **Backend:** FastAPI + SQLAlchemy 2 + Alembic, managed with [uv](https://docs.astral.sh/uv/)
- **Database:** PostgreSQL 18
- **Deploy:** Docker Compose (`db`, `api`, `web` = nginx serving the SPA and proxying `/api`)

## Ports

| What | Port |
|---|---|
| Postgres (dev, localhost only) | 5433 |
| API dev server | 8010 |
| Vite dev server | 5173 |
| Full Docker stack | 8338 (`WEB_PORT`, localhost only) |
| Mailpit (dev mailbox) | 8025 (web UI), 1025 (SMTP) |

## Local development

```sh
# 1. Database
docker compose up -d db mailpit

# 2. API (from backend/)
uv sync
uv run python -m alembic upgrade head
uv run python -m uvicorn app.main:app --port 8010 --reload

# 3. Frontend (from frontend/)
npm install
npm run dev            # http://localhost:5173 (proxies /api to :8010)
```

API docs: http://localhost:8010/api/docs

> **Windows note:** this machine's application control policy blocks unsigned `.exe` launchers in
> `.venv\Scripts` and the native libpq DLLs from `psycopg[binary]`. So:
> - run Python tools as modules: `uv run python -m pytest`, `python -m alembic`, `python -m uvicorn`
> - the database driver is **pg8000** (pure Python) instead of psycopg

### Common tasks

```sh
# Backend tests (from backend/) – uses a separate `mimre_test` database,
# created and migrated automatically; your dev data is never touched.
uv run python -m pytest

# New migration after changing app/models.py (from backend/)
uv run python -m alembic revision --autogenerate -m "describe change"

# Frontend type check + production build (from frontend/)
npm run build
```

## Accounts and login

Login is email + password, then a one-time code sent by email. There is no public sign-up:
accounts are created on the server with the admin CLI (from `backend/`):

```sh
uv run python -m app.cli create-user you@example.com   # asks for a password (min. 10 characters)
uv run python -m app.cli set-password you@example.com  # also logs out all devices
uv run python -m app.cli set-email old@example.com new@example.com
uv run python -m app.cli list-users
uv run python -m app.cli delete-user someone@example.com   # deletes the account AND all its data
```

In the Docker stack: `docker compose exec api python -m app.cli <command>`.

In development, login codes land in **Mailpit** at http://localhost:8025 (nothing leaves the machine).
In production, set `SMTP_*` and `MAIL_FROM` (see [.env.example](.env.example)).

**First time after upgrading from the single-user version:** existing data was given to the account
`owner@mimre.local`, which can't log in yet. Make it yours:

```sh
uv run python -m app.cli set-email owner@mimre.local you@example.com
uv run python -m app.cli set-password you@example.com
```

### Data isolation (read this before adding features)

Each user only ever sees their own data. This is enforced in three layers:

1. **API:** every endpoint except logging in requires a session (HttpOnly, Secure, SameSite cookie).
   Contact-data endpoints use `SessionDep` from [app/deps.py](backend/app/deps.py), which only exists
   for a logged-in user.
2. **Row-level security in Postgres:** every data table has an `owner_id` and a policy that only shows
   and accepts rows of the logged-in user (`app.user_id`, set per transaction in [app/db.py](backend/app/db.py)).
   The app connects as the restricted role `mimre_app`, which cannot bypass these policies. `owner_id` is
   filled in by the database, so application code never sets it.
3. **Foreign keys** include the owner, so a fact, note or relationship can never point at another user's person.

**When adding a table:** give it `owner_id = _owner_id()` (see [app/models.py](backend/app/models.py)),
reference people with `_owned_person_fk(...)`, and in the migration enable row-level security with an
`owner_only` policy (copy from the `users, authentication and row-level security` migration).
[tests/test_security.py](backend/tests/test_security.py) fails if any table lacks row-level security,
if any endpoint works without login, or if one user can reach another user's data.

## Install on iPhone (PWA)

Open Mimre in Safari, tap **Share → Add to Home Screen**. It then opens full screen with its own icon.
The service worker ([frontend/public/sw.js](frontend/public/sw.js)) caches the app shell so it starts
instantly and offline; API data is never cached. Service workers need HTTPS (or `localhost`), so offline
start on the phone works once the app is served over HTTPS (e.g. via Cloudflare Tunnel). The service worker
is only registered in production builds (`npm run build` / the Docker stack), not in `npm run dev`.

When changing caching behaviour in `sw.js`, bump the `CACHE` name so old caches are cleared.

## Continuous integration

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on every pull request and on pushes
to `main`: backend tests against a Postgres service container, and the frontend type check + build.
Work happens on branches and is merged to `main` via pull requests.

## Full stack in Docker

```sh
cp .env.example .env   # set a real POSTGRES_PASSWORD
docker compose up -d --build
```

Open http://localhost:8338. The API container runs migrations on startup. Login codes go to Mailpit
(http://localhost:8025) unless `SMTP_HOST` is set.

## Roadmap

1. ~~Skeleton: people CRUD, i18n, responsive layout, Docker~~
2. ~~Relationships (stored once, reverse label derived from gender; siblings/grandparents inferred), flexible facts, dated notes, fuzzy search across names, facts and notes~~
3. ~~PWA (installable on iPhone)~~
4. ~~User accounts with email code login, per-user data isolation (row-level security)~~
5. Deploy to Synology NAS behind Cloudflare Tunnel + Cloudflare Access; automated `pg_dump` backups
6. Map of where people live, birthday reminders, tags
