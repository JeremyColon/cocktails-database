from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.cache import close_cache, init_cache
from backend.config import settings
from backend.routers import auth, bar, cocktails
from backend.scraper.scheduler import scheduler

_dist = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_cache()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    await close_cache()


app = FastAPI(
    title="Cocktails API",
    description="Backend for the Cocktail Finder app",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cocktails.router)
app.include_router(bar.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve the React SPA — must come after all API routes.
if (_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    # Serve real files from dist (favicon, etc.); fall back to index.html for SPA routing.
    candidate = _dist / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(_dist / "index.html")
