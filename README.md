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
| Full Docker stack | 8338 (`WEB_PORT`) |

## Local development

```sh
# 1. Database
docker compose up -d db

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

Open http://localhost:8338. The API container runs migrations on startup.

## Roadmap

1. ~~Skeleton: people CRUD, i18n, responsive layout, Docker~~
2. ~~Relationships (stored once, reverse label derived from gender; siblings/grandparents inferred), flexible facts, dated notes, fuzzy search across names, facts and notes~~
3. ~~PWA (installable on iPhone)~~
4. Deploy to Synology NAS behind Cloudflare Tunnel + Cloudflare Access; automated `pg_dump` backups
5. Map of where people live, birthday reminders, tags
