"""AI-powered relevance scoring using Claude API."""

import asyncio
import json
import logging
from typing import Optional

import anthropic

from scrapers.base import Tender
from config import ANTHROPIC_API_KEY, AGENCY_PROFILE

logger = logging.getLogger(__name__)

SCORING_PROMPT = """Ти — експерт з аналізу тендерів для креативної маркетингової агенції.

Ось профіль агенції:
{agency_profile}

Проаналізуй наступний тендер і визнач, наскільки він релевантний для цієї агенції.

ТЕНДЕР:
- Назва: {title}
- Опис: {description}
- Замовник: {buyer}
- Бюджет: {budget}
- Країна: {country}
- CPV коди: {cpv_codes}
- Джерело: {source}

Оціни релевантність від 0 до 100:
- 80-100: Ідеально підходить — це саме те, що робить агенція
- 60-79: Дуже підходить — основна частина робіт відповідає профілю
- 40-59: Частково підходить — є релевантні компоненти
- 20-39: Слабо підходить — лише окремі елементи
- 0-19: Не підходить — не відповідає профілю агенції

Відповідай ТІЛЬКИ у форматі JSON:
{{"score": <число 0-100>, "reason": "<коротке пояснення українською, 1-2 речення>"}}
"""


async def score_tenders(tenders: list[Tender]) -> list[Tender]:
    """Score a list of tenders for relevance using Claude API."""
    if not ANTHROPIC_API_KEY:
        logger.warning("Anthropic API key not configured — skipping AI scoring")
        # Apply basic CPV-based scoring
        for t in tenders:
            t.relevance_score = _basic_cpv_score(t)
            t.relevance_reason = "Базова оцінка за CPV кодами (API ключ не налаштовано)"
        return sorted(tenders, key=lambda t: t.relevance_score, reverse=True)

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Process in batches to avoid rate limits
    batch_size = 5
    for i in range(0, len(tenders), batch_size):
        batch = tenders[i:i + batch_size]
        tasks = [_score_single_tender(client, t) for t in batch]
        await asyncio.gather(*tasks)
        if i + batch_size < len(tenders):
            await asyncio.sleep(1)  # Rate limiting between batches

    return sorted(tenders, key=lambda t: t.relevance_score, reverse=True)


async def _score_single_tender(
    client: anthropic.AsyncAnthropic,
    tender: Tender,
) -> None:
    """Score a single tender using Claude API."""
    try:
        prompt = SCORING_PROMPT.format(
            agency_profile=AGENCY_PROFILE,
            title=tender.title,
            description=tender.description[:1500] if tender.description else "Не вказано",
            buyer=tender.buyer or "Не вказано",
            budget=tender.budget_display,
            country=tender.country or "Не вказано",
            cpv_codes=", ".join(tender.cpv_codes) if tender.cpv_codes else "Не вказано",
            source=tender.source,
        )

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()

        # Parse JSON from response
        # Handle cases where model wraps JSON in markdown
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        tender.relevance_score = float(result.get("score", 0))
        tender.relevance_reason = result.get("reason", "")

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse AI score for '{tender.title[:50]}': {e}")
        tender.relevance_score = _basic_cpv_score(tender)
        tender.relevance_reason = "Базова оцінка (помилка AI парсингу)"
    except Exception as e:
        logger.error(f"AI scoring error for '{tender.title[:50]}': {e}")
        tender.relevance_score = _basic_cpv_score(tender)
        tender.relevance_reason = "Базова оцінка (помилка AI)"


def _basic_cpv_score(tender: Tender) -> float:
    """Fallback: basic relevance score based on CPV codes and keywords."""
    score = 30.0  # Base score for any tender that matched our search

    # CPV code matching
    high_relevance_cpv = {"79340000", "79341000", "79341400", "79342000", "79416000"}
    medium_relevance_cpv = {"79341100", "79341200", "79342100", "79342200", "79413000"}

    for cpv in tender.cpv_codes:
        cpv_prefix = cpv[:8] if len(cpv) >= 8 else cpv
        if cpv_prefix in high_relevance_cpv:
            score += 30
            break
        elif cpv_prefix in medium_relevance_cpv:
            score += 20
            break

    # Keyword matching in title/description
    text = f"{tender.title} {tender.description}".lower()
    high_keywords = ["рекламн", "маркетинг", "креатив", "брендинг", "advertising", "marketing", "creative", "branding"]
    medium_keywords = ["комунікац", "pr ", "медіа", "smm", "digital", "communication", "media", "public relations"]

    for kw in high_keywords:
        if kw in text:
            score += 15
            break

    for kw in medium_keywords:
        if kw in text:
            score += 10
            break

    return min(score, 100.0)
