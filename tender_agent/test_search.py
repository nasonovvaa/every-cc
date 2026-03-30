"""Quick test: run a single search to show results."""

import asyncio
import sys
import logging

import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger()

sys.path.insert(0, ".")
from scrapers.smarttender import search_smarttender
from scrapers.ungm import search_ungm
from scrapers.giz import search_giz
from scrapers.etender import search_etender
from scorer import score_tenders
from telegram_bot import _print_to_console


async def main():
    print("\n🚀 Rockets Tender Agent — тестовий пошук\n")
    all_tenders = []

    async with aiohttp.ClientSession() as session:
        sources = [
            ("SmartTender.biz 🇺🇦", search_smarttender(session, days_back=7)),
            ("UNGM 🇺🇳", search_ungm(session, days_back=14)),
            ("GIZ Ukraine 🇩🇪", search_giz(session, days_back=14)),
            ("E-Tender.ua 🇺🇦", search_etender(session, days_back=7)),
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
        _print_to_console(scored)
    else:
        print("Тендерів не знайдено (можливо, сайти тимчасово недоступні)")


if __name__ == "__main__":
    asyncio.run(main())
