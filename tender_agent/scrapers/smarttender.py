"""SmartTender.biz scraper."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from .base import Tender

logger = logging.getLogger(__name__)

SMARTTENDER_SEARCH_URL = "https://smarttender.biz/publichni-zakupivli-prozorro/"

# Keywords relevant for marketing/advertising agency
SEARCH_QUERIES = [
    "рекламні послуги",
    "маркетингові послуги",
    "комунікаційна кампанія",
    "PR послуги",
    "брендинг",
    "SMM",
    "інформаційна кампанія",
    "медіа",
    "креативні послуги",
    "виробництво відео",
    "контент",
    "просування",
]


async def search_smarttender(
    session: aiohttp.ClientSession,
    days_back: int = 7,
) -> list[Tender]:
    """Search smarttender.biz for relevant tenders."""
    tenders: list[Tender] = []
    seen_ids: set[str] = set()

    for query in SEARCH_QUERIES:
        try:
            found = await _search_keyword(session, query)
            for t in found:
                if t.tender_id not in seen_ids:
                    seen_ids.add(t.tender_id)
                    tenders.append(t)
        except Exception as e:
            logger.error(f"SmartTender search error ('{query}'): {e}")

    logger.info(f"SmartTender: found {len(tenders)} tenders")
    return tenders


async def _search_keyword(
    session: aiohttp.ClientSession,
    keyword: str,
) -> list[Tender]:
    """Search smarttender.biz by keyword."""
    tenders = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "uk-UA,uk;q=0.9",
    }

    try:
        params = {"query": keyword, "status": "active"}
        async with session.get(
            SMARTTENDER_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                logger.warning(f"SmartTender HTTP {resp.status} for '{keyword}'")
                return tenders

            html = await resp.text()
            soup = BeautifulSoup(html, "lxml")

            # SmartTender uses various listing formats
            items = soup.select(
                ".tender-list-item, .search-result-item, "
                ".table-row, tr.item, .tender-card"
            )

            for item in items[:30]:
                tender = _parse_item(item)
                if tender:
                    tenders.append(tender)

    except Exception as e:
        logger.error(f"SmartTender scraping error ('{keyword}'): {e}")

    return tenders


def _parse_item(item) -> Optional[Tender]:
    """Parse a single tender item from SmartTender HTML."""
    try:
        # Try various selectors for title
        title_elem = item.select_one(
            "a.tender-title, .title a, a[href*='tender'], "
            "td:nth-child(2) a, .tender-name a, h3 a, h4 a"
        )
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        if not title:
            return None

        href = title_elem.get("href", "")
        url = href if href.startswith("http") else f"https://smarttender.biz{href}"

        # Extract tender ID from URL or page
        tender_id = ""
        if href:
            parts = href.rstrip("/").split("/")
            tender_id = parts[-1] if parts else ""
        id_elem = item.select_one(".tender-id, .id, [data-tender-id]")
        if id_elem:
            tender_id = id_elem.get_text(strip=True) or id_elem.get("data-tender-id", tender_id)

        # Buyer / customer
        buyer_elem = item.select_one(
            ".customer, .buyer, .organization, "
            "td:nth-child(3), .tender-customer"
        )
        buyer = buyer_elem.get_text(strip=True) if buyer_elem else ""

        # Budget
        budget = None
        currency = "UAH"
        budget_elem = item.select_one(
            ".budget, .price, .amount, .tender-budget, "
            "td:nth-child(4), .expected-cost"
        )
        if budget_elem:
            budget_text = budget_elem.get_text(strip=True)
            budget, currency = _parse_budget(budget_text)

        # Deadline
        deadline = None
        deadline_elem = item.select_one(
            ".deadline, .end-date, .tender-deadline, "
            "td:nth-child(5), .date-end"
        )
        if deadline_elem:
            deadline = _parse_date(deadline_elem.get_text(strip=True))

        return Tender(
            source="smarttender",
            tender_id=tender_id or title[:50],
            title=title,
            description="",
            buyer=buyer,
            budget=budget,
            currency=currency,
            deadline=deadline,
            url=url,
            country="Україна",
            status="active",
        )
    except Exception as e:
        logger.debug(f"Error parsing SmartTender item: {e}")
        return None


def _parse_budget(text: str) -> tuple[Optional[float], str]:
    """Parse budget string like '1 500 000.00 UAH'."""
    import re
    text = text.strip()
    if not text or text == "—" or text == "-":
        return None, "UAH"

    currency = "UAH"
    if "EUR" in text.upper():
        currency = "EUR"
    elif "USD" in text.upper():
        currency = "USD"

    # Extract number
    cleaned = re.sub(r"[^\d.,]", "", text.replace(" ", ""))
    cleaned = cleaned.replace(",", ".")
    # Handle cases like "1500000.00"
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]

    try:
        return float(cleaned), currency
    except (ValueError, TypeError):
        return None, currency


def _parse_date(text: str) -> Optional[datetime]:
    """Parse date from various formats."""
    text = text.strip()
    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
