"""Telegram bot for tender notifications."""

import asyncio
import logging
from datetime import datetime, timezone

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scrapers.base import Tender

logger = logging.getLogger(__name__)


def _format_tender_message(tender: Tender) -> str:
    """Format a single tender in the requested message format."""
    budget = tender.budget_display
    deadline = tender.deadline_display

    return (
        "🆕 НОВИЙ ТЕНДЕР\n"
        f"📌 Назва: {tender.title}\n"
        f"🏢 Замовник: {tender.buyer or 'Не вказано'}\n"
        f"💰 Бюджет: {budget}\n"
        f"⏰ Дедлайн: {deadline}\n"
        f"🔗 Посилання: {tender.url or 'Не вказано'}"
    )


async def send_daily_digest(tenders: list[Tender]) -> None:
    """Send daily digest of new tenders to Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — printing to console")
        _print_to_console(tenders)
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    if not tenders:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=(
                f"📅 Дайджест тендерів — {datetime.now(timezone.utc).strftime('%d.%m.%Y')}\n\n"
                "Нових релевантних тендерів не знайдено.\n"
                "Наступна перевірка завтра о 9:00."
            ),
        )
        return

    # Send header
    header = (
        f"🚀 Дайджест тендерів — {datetime.now(timezone.utc).strftime('%d.%m.%Y')}\n"
        f"Знайдено нових тендерів: {len(tenders)}\n"
        f"{'─' * 30}"
    )
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=header)
    await asyncio.sleep(0.5)

    # Send each tender (max 20 to avoid spam)
    for tender in tenders[:20]:
        msg = _format_tender_message(tender)
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=msg,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Error sending tender: {e}")
        await asyncio.sleep(0.3)  # Avoid rate limits

    if len(tenders) > 20:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"... та ще {len(tenders) - 20} тендерів.",
        )


def _print_to_console(tenders: list[Tender]) -> None:
    """Print tenders to console (fallback when Telegram is not configured)."""
    print("\n" + "=" * 60)
    print(f"🚀 ДАЙДЖЕСТ ТЕНДЕРІВ — {datetime.now().strftime('%d.%m.%Y')}")
    print(f"Знайдено: {len(tenders)}")
    print("=" * 60)

    for tender in tenders[:20]:
        print()
        print(_format_tender_message(tender))
        print("─" * 50)

    print()


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
    await update.message.reply_text(
        "🚀 Rockets Tender Agent\n\n"
        "Я шукаю тендери для рекламної агенції на:\n"
        "• SmartTender.biz\n"
        "• UNGM.org\n"
        "• GIZ Ukraine\n"
        "• E-Tender.ua\n\n"
        "Команди:\n"
        "/search — Запустити пошук зараз\n"
        "/status — Статус агента\n"
        "/help — Допомога",
    )


async def _cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔍 Запускаю пошук тендерів... Це може зайняти 2-5 хвилин.")
    from main import run_daily_search
    try:
        count = await run_daily_search()
        await update.message.reply_text(f"✅ Пошук завершено! Знайдено {count} нових тендерів.")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка пошуку: {e}")


async def _cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from storage import get_sent_count
    count = get_sent_count()
    await update.message.reply_text(
        "🟢 Агент працює\n\n"
        "Джерела:\n"
        "• SmartTender.biz\n"
        "• UNGM.org\n"
        "• GIZ Ukraine\n"
        "• E-Tender.ua\n\n"
        f"Всього надіслано тендерів: {count}\n"
        "Автоматична перевірка: щодня о 9:00",
    )


async def _cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 Rockets Tender Agent — Допомога\n\n"
        "Агент щодня шукає тендери на рекламні, маркетингові "
        "та комунікаційні послуги.\n\n"
        "Фільтри: реклама, комунікації, PR, SMM, кампанії, "
        "awareness, соціальний маркетинг, медіа, брендинг, "
        "продакшн, контент.\n\n"
        "Команди:\n"
        "/search — Запустити пошук вручну\n"
        "/status — Статус агента\n"
        "/help — Ця довідка",
    )
