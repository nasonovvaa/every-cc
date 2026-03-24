"""Main orchestrator for Rockets Tender Agent."""

import asyncio
import logging
import sys

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import SEARCH_INTERVAL_HOURS, TELEGRAM_BOT_TOKEN
from scrapers.prozorro import search_prozorro
from scrapers.ted import search_ted
from scrapers.ungm import search_ungm
from scrapers.sam_gov import search_sam_gov
from scrapers.dgmarket import search_dgmarket, search_devex
from scrapers.base import Tender
from scorer import score_tenders
from telegram_bot import send_tender_report, setup_bot_commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tender_agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("tender_agent")


async def run_search(days_back: int = 7) -> list[Tender]:
    """Run tender search across all sources."""
    logger.info("=" * 50)
    logger.info("Starting tender search...")
    logger.info("=" * 50)

    all_tenders: list[Tender] = []

    async with aiohttp.ClientSession() as session:
        # Run all scrapers concurrently
        results = await asyncio.gather(
            search_prozorro(session, days_back=days_back),
            search_ted(session, days_back=days_back * 2),  # EU tenders updated less frequently
            search_ungm(session, days_back=days_back * 2),
            search_sam_gov(session, days_back=days_back * 2),
            search_dgmarket(session, days_back=days_back * 2),
            search_devex(session, days_back=days_back * 2),
            return_exceptions=True,
        )

        source_names = ["Prozorro", "TED", "UNGM", "SAM.gov", "DG Market", "Devex"]
        for name, result in zip(source_names, results):
            if isinstance(result, Exception):
                logger.error(f"{name} search failed: {result}")
            elif isinstance(result, list):
                all_tenders.extend(result)
                logger.info(f"{name}: {len(result)} tenders found")
            else:
                logger.warning(f"{name}: unexpected result type {type(result)}")

    logger.info(f"Total tenders collected: {len(all_tenders)}")

    # Deduplicate by title similarity
    all_tenders = _deduplicate(all_tenders)
    logger.info(f"After deduplication: {len(all_tenders)}")

    # AI relevance scoring
    logger.info("Running AI relevance scoring...")
    scored_tenders = await score_tenders(all_tenders)

    # Report results
    relevant_count = sum(1 for t in scored_tenders if t.relevance_score >= 40)
    logger.info(f"Relevant tenders (score >= 40): {relevant_count}")

    # Send to Telegram
    await send_tender_report(scored_tenders, min_score=40.0)

    return scored_tenders


def _deduplicate(tenders: list[Tender]) -> list[Tender]:
    """Remove duplicate tenders based on ID and title similarity."""
    seen: dict[str, Tender] = {}
    unique: list[Tender] = []

    for tender in tenders:
        # Deduplicate by exact ID + source
        key = f"{tender.source}:{tender.tender_id}"
        if key in seen:
            continue

        # Simple title-based dedup (normalize and check)
        title_key = tender.title.lower().strip()[:80]
        if title_key and title_key in seen:
            # Keep the one with more info
            existing = seen[title_key]
            if len(tender.description) > len(existing.description):
                unique.remove(existing)
                unique.append(tender)
                seen[title_key] = tender
            continue

        seen[key] = tender
        if title_key:
            seen[title_key] = tender
        unique.append(tender)

    return unique


async def main():
    """Main entry point."""
    logger.info("🚀 Rockets Tender Agent starting...")

    # Run initial search
    await run_search()

    # Set up scheduler for periodic searches
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_search,
        "interval",
        hours=SEARCH_INTERVAL_HOURS,
        id="tender_search",
        name="Periodic tender search",
    )
    scheduler.start()
    logger.info(f"Scheduler started: searching every {SEARCH_INTERVAL_HOURS} hours")

    # If Telegram bot is configured, run it for interactive commands
    if TELEGRAM_BOT_TOKEN:
        logger.info("Starting Telegram bot...")
        app = await setup_bot_commands()
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram bot is running. Press Ctrl+C to stop.")

        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            scheduler.shutdown()
    else:
        logger.info("Telegram not configured. Running in console mode.")
        logger.info("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env for Telegram integration.")
        # Keep scheduler running
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
            scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
