"""DG Market and other international tender aggregators scraper."""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import aiohttp
from bs4 import BeautifulSoup

from .base import Tender

logger = logging.getLogger(__name__)


async def search_dgmarket(
    session: aiohttp.ClientSession,
    days_back: int = 14,
) -> list[Tender]:
    """Search DG Market for international development tenders."""
    tenders: list[Tender] = []
    seen_ids: set[str] = set()

    keywords = [
        "advertising services",
        "marketing campaign",
        "communication campaign",
        "creative agency",
        "public relations",
        "branding",
        "media services",
    ]

    for keyword in keywords:
        kw_tenders = await _scrape_dgmarket(session, keyword)
        for t in kw_tenders:
            if t.tender_id not in seen_ids:
                seen_ids.add(t.tender_id)
                tenders.append(t)
        await asyncio.sleep(1)  # Be polite

    logger.info(f"DG Market: found {len(tenders)} tenders")
    return tenders


async def _scrape_dgmarket(
    session: aiohttp.ClientSession,
    keyword: str,
) -> list[Tender]:
    """Scrape DG Market search results."""
    tenders = []
    base_url = "https://www.dgmarket.com/tenders/searchResult.do"

    try:
        params = {
            "searchString": keyword,
            "noticeType": "gpn,sp",  # General procurement notice + specific procurement
            "status": "open",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }

        async with session.get(
            f"{base_url}?{urlencode(params)}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                logger.warning(f"DG Market search '{keyword}': HTTP {resp.status}")
                return tenders

            html = await resp.text()
            soup = BeautifulSoup(html, "lxml")

            # Parse result rows
            rows = soup.select("table.resultTable tr, div.tender-item, .search-result-item")

            for row in rows[:20]:
                try:
                    title_elem = row.select_one("a.tenderTitle, td.title a, a[href*='tender']")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    tender_id = href.split("/")[-1] if href else title[:50]

                    # Try to find org/buyer
                    org_elem = row.select_one("td.organization, .buyer, .organization")
                    org = org_elem.get_text(strip=True) if org_elem else ""

                    # Country
                    country_elem = row.select_one("td.country, .country")
                    country = country_elem.get_text(strip=True) if country_elem else "International"

                    # Deadline
                    deadline_elem = row.select_one("td.deadline, .deadline, .closing-date")
                    deadline = None
                    if deadline_elem:
                        dl_text = deadline_elem.get_text(strip=True)
                        for fmt in ["%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
                            try:
                                deadline = datetime.strptime(dl_text, fmt)
                                break
                            except ValueError:
                                continue

                    url = f"https://www.dgmarket.com{href}" if href.startswith("/") else href

                    tenders.append(Tender(
                        source="dgmarket",
                        tender_id=tender_id,
                        title=title,
                        description="",
                        buyer=org,
                        currency="USD",
                        deadline=deadline,
                        url=url,
                        country=country,
                    ))
                except Exception:
                    continue

    except Exception as e:
        logger.error(f"DG Market scraping error ('{keyword}'): {e}")

    return tenders


async def search_devex(
    session: aiohttp.ClientSession,
    days_back: int = 14,
) -> list[Tender]:
    """Search Devex for international development opportunities."""
    tenders: list[Tender] = []

    keywords = [
        "marketing communication",
        "advertising campaign",
        "public awareness campaign",
        "creative services",
    ]

    for keyword in keywords:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            url = f"https://www.devex.com/funding/search?q={keyword}&type=tenders&status=open"

            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    continue

                html = await resp.text()
                soup = BeautifulSoup(html, "lxml")
                items = soup.select("article.funding-item, .search-result, .opportunity-card")

                for item in items[:15]:
                    try:
                        title_elem = item.select_one("h3 a, .title a, a.opportunity-title")
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        href = title_elem.get("href", "")
                        tender_id = href.split("/")[-1] if href else ""

                        org_elem = item.select_one(".organization, .funder, .source")
                        org = org_elem.get_text(strip=True) if org_elem else ""

                        deadline_elem = item.select_one(".deadline, .date, time")
                        deadline = None
                        if deadline_elem:
                            dl_text = deadline_elem.get("datetime", deadline_elem.get_text(strip=True))
                            try:
                                deadline = datetime.fromisoformat(dl_text)
                            except (ValueError, TypeError):
                                pass

                        item_url = f"https://www.devex.com{href}" if href.startswith("/") else href

                        tenders.append(Tender(
                            source="dgmarket",
                            tender_id=f"devex-{tender_id}",
                            title=title,
                            description="",
                            buyer=org,
                            currency="USD",
                            deadline=deadline,
                            url=item_url,
                            country="International",
                        ))
                    except Exception:
                        continue

        except Exception as e:
            logger.error(f"Devex scraping error ('{keyword}'): {e}")
        await asyncio.sleep(1)

    logger.info(f"Devex: found {len(tenders)} tenders")
    return tenders
