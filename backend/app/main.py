from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import facts, me, notes, persons, relationships

app = FastAPI(title="Mimre API", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


@api.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


api.include_router(persons.router)
api.include_router(me.router)
api.include_router(relationships.router)
api.include_router(facts.router)
api.include_router(notes.router)
app.include_router(api)
