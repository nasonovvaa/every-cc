"""Main orchestrator for Rockets Tender Agent.

Monitors 4 tender platforms daily:
- smarttender.biz
- ungm.org
- giz.de/en/ukraina/tenders
- e-tender.ua

Filters for marketing/advertising relevance and sends digest to Telegram.
"""

import asyncio
import logging
import sys

import aiohttp

from config import TELEGRAM_BOT_TOKEN
from scrapers.smarttender import search_smarttender
from scrapers.ungm import search_ungm
from scrapers.giz import search_giz
from scrapers.etender import search_etender
from scrapers.base import Tender
from scorer import score_tenders
from storage import filter_new_tenders, mark_batch_as_sent
from telegram_bot import send_daily_digest, setup_bot_commands

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


async def run_daily_search() -> int:
    """Run tender search across all 4 sources and send digest.

    Returns the number of new tenders sent.
    """
    logger.info("=" * 50)
    logger.info("Starting daily tender search...")
    logger.info("=" * 50)

    all_tenders: list[Tender] = []

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            search_smarttender(session, days_back=7),
            search_ungm(session, days_back=14),
            search_giz(session, days_back=14),
            search_etender(session, days_back=7),
            return_exceptions=True,
        )

        source_names = ["SmartTender", "UNGM", "GIZ", "E-Tender"]
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
    logger.info("Running relevance scoring...")
    scored_tenders = await score_tenders(all_tenders)

    # Filter relevant tenders (score >= 40)
    relevant = [t for t in scored_tenders if t.relevance_score >= 40]
    logger.info(f"Relevant tenders (score >= 40): {len(relevant)}")

    # Filter out already sent tenders
    new_tenders = filter_new_tenders(relevant)
    logger.info(f"New tenders (not yet sent): {len(new_tenders)}")

    # Send to Telegram
    await send_daily_digest(new_tenders)

    # Mark as sent
    mark_batch_as_sent(new_tenders)

    return len(new_tenders)


def _deduplicate(tenders: list[Tender]) -> list[Tender]:
    """Remove duplicate tenders based on ID and title similarity."""
    seen: dict[str, Tender] = {}
    unique: list[Tender] = []

    for tender in tenders:
        key = f"{tender.source}:{tender.tender_id}"
        if key in seen:
            continue

        title_key = tender.title.lower().strip()[:80]
        if title_key and title_key in seen:
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

    # Check if running as one-shot (e.g. from GitHub Actions)
    if "--once" in sys.argv:
        count = await run_daily_search()
        logger.info(f"One-shot search complete. Sent {count} new tenders.")
        return

    # Run initial search
    await run_daily_search()

    # If Telegram bot is configured, run it for interactive commands
    if TELEGRAM_BOT_TOKEN:
        logger.info("Starting Telegram bot...")
        app = await setup_bot_commands()
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram bot is running. Press Ctrl+C to stop.")

        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
    else:
        logger.info("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")


if __name__ == "__main__":
    asyncio.run(main())
