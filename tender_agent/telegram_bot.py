"""Telegram bot for tender notifications."""

import asyncio
import logging
from datetime import datetime, timezone

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.base import Tender

logger = logging.getLogger(__name__)

# Store last search results for reference
_last_results: list[Tender] = []


async def send_tender_report(tenders: list[Tender], min_score: float = 40.0) -> None:
    """Send tender report to Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — printing to console")
        _print_to_console(tenders, min_score)
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    # Filter by minimum relevance score
    relevant = [t for t in tenders if t.relevance_score >= min_score]

    if not relevant:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=(
                "🔍 <b>Звіт по тендерах</b>\n\n"
                f"📅 {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')} UTC\n\n"
                f"Перевірено тендерів: {len(tenders)}\n"
                f"Релевантних (>{min_score:.0f}%): 0\n\n"
                "Нових підходящих тендерів не знайдено. "
                "Наступна перевірка за 6 годин."
            ),
            parse_mode="HTML",
        )
        return

    # Send summary header
    sources_count = {}
    for t in relevant:
        sources_count[t.source] = sources_count.get(t.source, 0) + 1

    source_stats = ", ".join(
        f"{s}: {c}" for s, c in sorted(sources_count.items(), key=lambda x: -x[1])
    )

    header = (
        "🚀 <b>Rockets Tender Agent — Звіт</b>\n\n"
        f"📅 {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')} UTC\n"
        f"🔍 Перевірено тендерів: {len(tenders)}\n"
        f"✅ Релевантних: {len(relevant)}\n"
        f"📊 Джерела: {source_stats}\n"
        f"\n{'─' * 30}\n"
    )
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=header, parse_mode="HTML")
    await asyncio.sleep(0.5)

    # Send top tenders (max 15 to avoid spam)
    top_tenders = relevant[:15]
    for i, tender in enumerate(top_tenders, 1):
        msg = f"<b>#{i}</b>\n{tender.to_telegram_message()}"
        try:
            # Add inline button to view tender
            keyboard = None
            if tender.url:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Відкрити тендер", url=tender.url)]
                ])
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=msg,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Error sending tender #{i}: {e}")
        await asyncio.sleep(0.3)  # Avoid rate limits

    # Send footer
    if len(relevant) > 15:
        footer = f"\n... та ще {len(relevant) - 15} тендерів. Використайте /all для повного списку."
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=footer, parse_mode="HTML")


def _print_to_console(tenders: list[Tender], min_score: float) -> None:
    """Print tenders to console (fallback when Telegram is not configured)."""
    relevant = [t for t in tenders if t.relevance_score >= min_score]

    print("\n" + "=" * 60)
    print("🚀 ROCKETS TENDER AGENT — ЗВІТ")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"🔍 Перевірено: {len(tenders)} | Релевантних: {len(relevant)}")
    print("=" * 60)

    for i, tender in enumerate(relevant[:20], 1):
        print(f"\n{'─' * 50}")
        print(f"#{i} | Score: {tender.relevance_score:.0f}/100 | {tender.source.upper()}")
        print(f"📌 {tender.title}")
        print(f"🏢 {tender.buyer}")
        print(f"💰 {tender.budget_display}")
        print(f"📅 Дедлайн: {tender.deadline_display}")
        if tender.country:
            print(f"📍 {tender.country}")
        if tender.relevance_reason:
            print(f"💡 {tender.relevance_reason}")
        if tender.url:
            print(f"🔗 {tender.url}")

    print("\n" + "=" * 60)


async def setup_bot_commands() -> Application:
    """Set up the Telegram bot with command handlers."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("search", _cmd_search))
    app.add_handler(CommandHandler("status", _cmd_status))
    app.add_handler(CommandHandler("help", _cmd_help))

    return app


async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "🚀 <b>Rockets Tender Agent</b>\n\n"
        "Я шукаю тендери на рекламні та маркетингові послуги "
        "на Prozorro, TED (EU), UNGM (UN), SAM.gov (US) та інших платформах.\n\n"
        "Команди:\n"
        "/search — Запустити пошук зараз\n"
        "/status — Статус агента\n"
        "/help — Допомога\n\n"
        "Автоматичний пошук запускається кожні 6 годин.",
        parse_mode="HTML",
    )


async def _cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command — trigger manual search."""
    await update.message.reply_text("🔍 Запускаю пошук тендерів... Це може зайняти 2-5 хвилин.")
    # The actual search is triggered via the main orchestrator
    from main import run_search
    try:
        await run_search()
        await update.message.reply_text("✅ Пошук завершено! Результати надіслано вище.")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка пошуку: {e}")


async def _cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    await update.message.reply_text(
        "🟢 <b>Агент працює</b>\n\n"
        "Джерела пошуку:\n"
        "• 🇺🇦 Prozorro\n"
        "• 🇪🇺 TED (EU)\n"
        "• 🇺🇳 UNGM (UN)\n"
        "• 🇺🇸 SAM.gov (US)\n"
        "• 🌍 DG Market / Devex\n\n"
        "Мінімальний бюджет: 1 000 000 грн\n"
        "Інтервал пошуку: кожні 6 годин",
        parse_mode="HTML",
    )


async def _cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "📖 <b>Rockets Tender Agent — Допомога</b>\n\n"
        "<b>Як це працює:</b>\n"
        "Агент автоматично шукає тендери на рекламні, маркетингові "
        "та комунікаційні послуги на українських та міжнародних платформах.\n\n"
        "Кожен тендер оцінюється AI за релевантністю для агенції Rockets "
        "(маркетинг, реклама, PR, брендинг, digital).\n\n"
        "<b>Команди:</b>\n"
        "/search — Запустити пошук вручну\n"
        "/status — Статус агента\n"
        "/help — Ця довідка\n\n"
        "<b>Оцінка релевантності:</b>\n"
        "⭐⭐⭐⭐⭐ 80-100: Ідеально підходить\n"
        "⭐⭐⭐⭐ 60-79: Дуже підходить\n"
        "⭐⭐⭐ 40-59: Частково підходить\n"
        "⭐⭐ 20-39: Слабо підходить",
        parse_mode="HTML",
    )
