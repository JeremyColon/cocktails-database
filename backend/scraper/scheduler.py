import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.scraper.pipeline import run_pipeline

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Run every Monday at 3 AM server time
scheduler.add_job(
    run_pipeline,
    trigger="cron",
    day_of_week="mon",
    hour=3,
    minute=0,
    id="weekly_scrape",
    name="Weekly cocktail scrape",
    replace_existing=True,
    misfire_grace_time=3600,   # allow up to 1hr late start (e.g. after dyno sleep)
)

logger.info("Scraper scheduled: Mondays at 03:00")
