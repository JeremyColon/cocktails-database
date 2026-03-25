from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.cache import close_cache, init_cache
from backend.routers import auth, bar, cocktails
from backend.scraper.scheduler import scheduler


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
    allow_origins=["http://localhost:5173"],  # Vite dev server; update for production
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
