"""Quick test: run a single search to show results."""

import asyncio
import sys
import logging

import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger()

sys.path.insert(0, ".")
from scrapers.prozorro import search_prozorro
from scrapers.ted import search_ted
from scrapers.ungm import search_ungm
from scrapers.dgmarket import search_dgmarket
from scorer import score_tenders
from telegram_bot import _print_to_console


async def main():
    print("\n🚀 Rockets Tender Agent — тестовий пошук\n")
    all_tenders = []

    async with aiohttp.ClientSession() as session:
        # Search all available sources (no API key needed)
        sources = [
            ("Prozorro 🇺🇦", search_prozorro(session, days_back=7)),
            ("TED 🇪🇺", search_ted(session, days_back=14)),
            ("UNGM 🇺🇳", search_ungm(session, days_back=14)),
            ("DG Market 🌍", search_dgmarket(session, days_back=14)),
        ]

        for name, coro in sources:
            try:
                print(f"🔍 Шукаю на {name}...")
                results = await coro
                print(f"   ✅ Знайдено: {len(results)}")
                all_tenders.extend(results)
            except Exception as e:
                print(f"   ⚠️  Помилка: {e}")

    print(f"\n📊 Всього зібрано: {len(all_tenders)} тендерів")

    if all_tenders:
        print("🤖 Оцінюю релевантність (базова оцінка без AI)...")
        scored = await score_tenders(all_tenders)
        _print_to_console(scored, min_score=20.0)
    else:
        print("Тендерів не знайдено (можливо, API тимчасово недоступні)")


if __name__ == "__main__":
    asyncio.run(main())
