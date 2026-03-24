"""UNGM (United Nations Global Marketplace) tender scraper."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from .base import Tender
from config import SEARCH_KEYWORDS_EN, MIN_BUDGET_USD

logger = logging.getLogger(__name__)

UNGM_SEARCH_URL = "https://www.ungm.org/Public/Notice"
UNGM_API_URL = "https://www.ungm.org/api/Public/Notice"
UNGM_NOTICE_URL = "https://www.ungm.org/Public/Notice/{notice_id}"


async def search_ungm(
    session: aiohttp.ClientSession,
    days_back: int = 14,
) -> list[Tender]:
    """Search UNGM for relevant UN tenders."""
    tenders: list[Tender] = []
    seen_ids: set[str] = set()

    keywords = [
        "advertising", "marketing", "creative agency",
        "communication campaign", "branding", "PR services",
        "media planning", "public relations", "digital marketing",
        "information campaign",
    ]

    for keyword in keywords:
        kw_tenders = await _search_ungm_keyword(session, keyword, days_back)
        for t in kw_tenders:
            if t.tender_id not in seen_ids:
                seen_ids.add(t.tender_id)
                tenders.append(t)

    logger.info(f"UNGM: found {len(tenders)} tenders")
    return tenders


async def _search_ungm_keyword(
    session: aiohttp.ClientSession,
    keyword: str,
    days_back: int,
) -> list[Tender]:
    """Search UNGM by keyword using the API."""
    tenders = []
    deadline_from = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")

    try:
        # UNGM has a JSON API for searching notices
        payload = {
            "Title": keyword,
            "Description": "",
            "Reference": "",
            "PublishedFrom": (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00"),
            "PublishedTo": datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59"),
            "DeadlineFrom": deadline_from,
            "PageIndex": 0,
            "PageSize": 20,
            "SortField": "DatePublished",
            "SortAscending": False,
            "isPagingEnabled": True,
            "NoticeTASStatus": [],
            "UNSPSCCodes": [],
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; TenderBot/1.0)",
        }

        async with session.post(
            UNGM_API_URL, json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                # Fallback to scraping
                return await _scrape_ungm_keyword(session, keyword)
            data = await resp.json()
            notices = data if isinstance(data, list) else data.get("Results", data.get("results", []))
            for notice in notices:
                tender = _parse_ungm_notice(notice)
                if tender:
                    tenders.append(tender)
    except Exception as e:
        logger.error(f"UNGM API search error ('{keyword}'): {e}")
        return await _scrape_ungm_keyword(session, keyword)

    return tenders


async def _scrape_ungm_keyword(
    session: aiohttp.ClientSession,
    keyword: str,
) -> list[Tender]:
    """Fallback: scrape UNGM search page."""
    tenders = []
    try:
        params = {"searchedKeyword": keyword}
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TenderBot/1.0)"}

        async with session.get(
            UNGM_SEARCH_URL, params=params, headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                return tenders
            html = await resp.text()
            soup = BeautifulSoup(html, "lxml")
            rows = soup.select("tr.ungm-list-item, div.notice-item, .tableRow")

            for row in rows[:20]:
                try:
                    title_elem = row.select_one("a.notice-title, .title a, td:nth-child(2) a")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    notice_id = href.split("/")[-1] if href else ""

                    org_elem = row.select_one(".organization, td:nth-child(3)")
                    org = org_elem.get_text(strip=True) if org_elem else ""

                    deadline_elem = row.select_one(".deadline, td:nth-child(4)")
                    deadline_str = deadline_elem.get_text(strip=True) if deadline_elem else ""
                    deadline = None
                    if deadline_str:
                        try:
                            deadline = datetime.strptime(deadline_str, "%d-%b-%Y")
                        except ValueError:
                            pass

                    url = f"https://www.ungm.org{href}" if href.startswith("/") else href

                    tenders.append(Tender(
                        source="ungm",
                        tender_id=notice_id,
                        title=title,
                        description="",
                        buyer=org,
                        budget=None,
                        currency="USD",
                        deadline=deadline,
                        url=url,
                        country="International",
                    ))
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"UNGM scraping error ('{keyword}'): {e}")

    return tenders


def _parse_ungm_notice(notice: dict) -> Optional[Tender]:
    """Parse a UNGM API notice into a Tender object."""
    try:
        notice_id = str(notice.get("Id", notice.get("id", "")))
        title = notice.get("Title", notice.get("title", ""))
        description = notice.get("Description", notice.get("description", ""))

        # Organization
        org = notice.get("AgencyName", notice.get("Organization", ""))
        if isinstance(org, dict):
            org = org.get("Name", "")

        # Deadline
        deadline = None
        dl = notice.get("Deadline", notice.get("DeadlineDate", ""))
        if dl:
            try:
                deadline = datetime.fromisoformat(str(dl).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Published
        published = None
        pd = notice.get("PublishedDate", notice.get("DatePublished", ""))
        if pd:
            try:
                published = datetime.fromisoformat(str(pd).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        url = UNGM_NOTICE_URL.format(notice_id=notice_id)

        return Tender(
            source="ungm",
            tender_id=notice_id,
            title=title,
            description=description[:2000] if description else "",
            buyer=org if isinstance(org, str) else "",
            budget=None,  # UNGM often doesn't show budgets publicly
            currency="USD",
            deadline=deadline,
            published=published,
            url=url,
            country="International",
            status="active",
        )
    except Exception as e:
        logger.error(f"Error parsing UNGM notice: {e}")
        return None
