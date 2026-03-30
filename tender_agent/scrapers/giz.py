"""GIZ Ukraine tenders scraper."""

import logging
from datetime import datetime, timezone
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from .base import Tender

logger = logging.getLogger(__name__)

GIZ_TENDERS_URL = "https://www.giz.de/en/ukraina/tenders"


async def search_giz(
    session: aiohttp.ClientSession,
    days_back: int = 14,
) -> list[Tender]:
    """Scrape GIZ Ukraine tenders page."""
    tenders: list[Tender] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with session.get(
            GIZ_TENDERS_URL,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                logger.warning(f"GIZ HTTP {resp.status}")
                return tenders

            html = await resp.text()
            soup = BeautifulSoup(html, "lxml")

            # GIZ tenders are typically listed in content blocks or tables
            # Try multiple selectors for different page layouts
            items = soup.select(
                ".tender-item, .content-item, article, "
                ".teaser, .list-item, .box, .panel, "
                "table tbody tr, .accordion-item, "
                ".text-media, section .row"
            )

            for item in items:
                tender = _parse_giz_item(item)
                if tender:
                    tenders.append(tender)

            # Also try to find tenders in text blocks with links
            if not tenders:
                tenders = _parse_giz_text_blocks(soup)

    except Exception as e:
        logger.error(f"GIZ scraping error: {e}")

    logger.info(f"GIZ Ukraine: found {len(tenders)} tenders")
    return tenders


def _parse_giz_item(item) -> Optional[Tender]:
    """Parse a GIZ tender item."""
    try:
        # Find title link
        title_elem = item.select_one(
            "a[href*='tender'], a[href*='procurement'], "
            "h2 a, h3 a, h4 a, .title a, a.teaser-link, "
            "a[href*='.pdf'], a[href*='giz.de']"
        )
        if not title_elem:
            # Try getting title from heading and link separately
            heading = item.select_one("h2, h3, h4, .title, strong")
            link = item.select_one("a[href]")
            if heading and link:
                title = heading.get_text(strip=True)
                href = link.get("href", "")
            else:
                return None
        else:
            title = title_elem.get_text(strip=True)
            href = title_elem.get("href", "")

        if not title or len(title) < 10:
            return None

        # Skip obviously irrelevant items (navigation, headers, etc.)
        skip_words = ["cookie", "privacy", "imprint", "contact", "menu", "navigation"]
        if any(w in title.lower() for w in skip_words):
            return None

        url = href if href.startswith("http") else f"https://www.giz.de{href}"

        # Try to find deadline
        deadline = None
        deadline_elem = item.select_one(
            ".date, .deadline, time, [datetime], "
            "td:nth-child(2), .meta-date"
        )
        if deadline_elem:
            date_text = deadline_elem.get("datetime", "") or deadline_elem.get_text(strip=True)
            deadline = _parse_date(date_text)

        # Extract description
        desc_elem = item.select_one("p, .description, .text, .summary")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        tender_id = href.rstrip("/").split("/")[-1] if href else title[:50]

        return Tender(
            source="giz",
            tender_id=f"giz-{tender_id}",
            title=title,
            description=description[:2000],
            buyer="GIZ (Deutsche Gesellschaft für Internationale Zusammenarbeit)",
            budget=None,
            currency="EUR",
            deadline=deadline,
            url=url,
            country="Україна",
            status="active",
        )
    except Exception as e:
        logger.debug(f"Error parsing GIZ item: {e}")
        return None


def _parse_giz_text_blocks(soup: BeautifulSoup) -> list[Tender]:
    """Fallback: parse GIZ page looking for tender-related text blocks."""
    tenders = []
    # Look for all links that might be tender documents
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        text = link.get_text(strip=True)

        # Filter for links that look like tenders
        tender_indicators = [
            "tender", "procurement", "rfp", "rfq", "rfi",
            "bid", "proposal", "consultancy", "services",
        ]
        if not any(ind in (href + text).lower() for ind in tender_indicators):
            continue

        if len(text) < 15:
            continue

        url = href if href.startswith("http") else f"https://www.giz.de{href}"
        tender_id = href.rstrip("/").split("/")[-1] if href else text[:50]

        tenders.append(Tender(
            source="giz",
            tender_id=f"giz-{tender_id}",
            title=text,
            description="",
            buyer="GIZ (Deutsche Gesellschaft für Internationale Zusammenarbeit)",
            budget=None,
            currency="EUR",
            deadline=None,
            url=url,
            country="Україна",
            status="active",
        ))

    return tenders


def _parse_date(text: str) -> Optional[datetime]:
    """Parse date from various formats."""
    text = text.strip()
    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d %B %Y",
        "%B %d, %Y",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
