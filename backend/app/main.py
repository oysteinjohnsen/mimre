from fastapi import APIRouter, FastAPI

from app.routers import auth, facts, me, notes, persons, relationships

# The frontend is served from the same origin as the API (nginx in production, the Vite proxy in
# development), so no CORS is configured: other sites' scripts can't call the API.
app = FastAPI(title="Mimre API", docs_url="/api/docs", openapi_url="/api/openapi.json")

api = APIRouter(prefix="/api")


@api.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Public: logging in. Everything else requires a logged-in user (see app.deps.SessionDep).
api.include_router(auth.router)

api.include_router(persons.router)
api.include_router(me.router)
api.include_router(relationships.router)
api.include_router(facts.router)
api.include_router(notes.router)
app.include_router(api)
