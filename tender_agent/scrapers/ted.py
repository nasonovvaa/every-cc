"""TED (Tenders Electronic Daily) — EU procurement platform scraper."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp

from .base import Tender
from config import SEARCH_KEYWORDS_EN, RELEVANT_CPV_CODES, MIN_BUDGET_EUR

logger = logging.getLogger(__name__)

# TED API (public search)
TED_SEARCH_API = "https://ted.europa.eu/api/v3.0/notices/search"
TED_NOTICE_URL = "https://ted.europa.eu/en/notice/-/detail/{notice_id}"


async def search_ted(
    session: aiohttp.ClientSession,
    days_back: int = 14,
) -> list[Tender]:
    """Search TED for relevant EU tenders."""
    tenders: list[Tender] = []
    seen_ids: set[str] = set()

    # Strategy 1: Search by CPV codes
    cpv_tenders = await _search_ted_by_cpv(session, days_back)
    for t in cpv_tenders:
        if t.tender_id not in seen_ids:
            seen_ids.add(t.tender_id)
            tenders.append(t)

    # Strategy 2: Search by keywords
    for keyword in SEARCH_KEYWORDS_EN[:8]:
        kw_tenders = await _search_ted_by_keyword(session, keyword, days_back)
        for t in kw_tenders:
            if t.tender_id not in seen_ids:
                seen_ids.add(t.tender_id)
                tenders.append(t)
        await asyncio.sleep(0.5)

    logger.info(f"TED: found {len(tenders)} tenders")
    return tenders


async def _search_ted_by_cpv(
    session: aiohttp.ClientSession,
    days_back: int,
) -> list[Tender]:
    """Search TED by CPV codes."""
    tenders = []
    date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y%m%d")
    date_to = datetime.now(timezone.utc).strftime("%Y%m%d")

    # Top CPV codes for advertising/marketing
    cpv_query = " OR ".join([f"cpv={c}" for c in ["79340000", "79341000", "79342000", "79416000"]])
    query = f"({cpv_query}) AND PD=[{date_from} <> {date_to}]"

    try:
        params = {
            "q": query,
            "pageSize": 50,
            "pageNum": 1,
            "scope": "3",  # Active notices
        }
        async with session.get(
            TED_SEARCH_API, params=params, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                # Fallback: try the RSS/legacy search
                return await _search_ted_legacy(session, days_back)
            data = await resp.json()
            notices = data.get("notices", data.get("results", []))
            for notice in notices:
                tender = _parse_ted_notice(notice)
                if tender:
                    tenders.append(tender)
    except Exception as e:
        logger.error(f"TED CPV search error: {e}")
        return await _search_ted_legacy(session, days_back)

    return tenders


async def _search_ted_by_keyword(
    session: aiohttp.ClientSession,
    keyword: str,
    days_back: int,
) -> list[Tender]:
    """Search TED by keyword."""
    tenders = []
    date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y%m%d")
    date_to = datetime.now(timezone.utc).strftime("%Y%m%d")

    try:
        params = {
            "q": f'TI="{keyword}" AND PD=[{date_from} <> {date_to}]',
            "pageSize": 20,
            "pageNum": 1,
            "scope": "3",
        }
        async with session.get(
            TED_SEARCH_API, params=params, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                return tenders
            data = await resp.json()
            notices = data.get("notices", data.get("results", []))
            for notice in notices:
                tender = _parse_ted_notice(notice)
                if tender:
                    tenders.append(tender)
    except Exception as e:
        logger.error(f"TED keyword search error ('{keyword}'): {e}")

    return tenders


async def _search_ted_legacy(
    session: aiohttp.ClientSession,
    days_back: int,
) -> list[Tender]:
    """Fallback: search TED via legacy/RSS endpoint."""
    tenders = []
    base_url = "https://ted.europa.eu/api/v2.0/notices/search"

    for cpv in ["79340000", "79341000", "79342000", "79416000"]:
        try:
            params = {
                "q": f"cpv:{cpv}",
                "limit": 50,
                "scope": 3,
            }
            async with session.get(
                base_url, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                for item in data.get("results", data.get("notices", [])):
                    tender = _parse_ted_notice(item)
                    if tender:
                        tenders.append(tender)
        except Exception as e:
            logger.debug(f"TED legacy search error ({cpv}): {e}")
        await asyncio.sleep(0.3)

    return tenders


def _parse_ted_notice(notice: dict) -> Optional[Tender]:
    """Parse a TED notice into a Tender object."""
    try:
        notice_id = notice.get("noticeId", notice.get("tedNoDocOjs", notice.get("id", "")))
        title = (
            notice.get("title", {}).get("en", "")
            if isinstance(notice.get("title"), dict)
            else notice.get("title", notice.get("titleText", ""))
        )
        description = (
            notice.get("description", {}).get("en", "")
            if isinstance(notice.get("description"), dict)
            else notice.get("description", notice.get("shortDescription", ""))
        )

        # Budget
        budget = None
        currency = "EUR"
        value = notice.get("estimatedValue", notice.get("totalValue", {}))
        if isinstance(value, dict):
            budget = value.get("amount", value.get("value"))
            currency = value.get("currency", "EUR")
        elif isinstance(value, (int, float)):
            budget = float(value)

        # Filter by minimum budget
        if budget is not None and budget < MIN_BUDGET_EUR:
            return None

        # Buyer
        buyer = ""
        org = notice.get("buyerName", notice.get("organisationName", notice.get("contractingBody", {})))
        if isinstance(org, dict):
            buyer = org.get("en", org.get("officialName", ""))
        elif isinstance(org, str):
            buyer = org

        # Deadline
        deadline = None
        dl = notice.get("deadlineDate", notice.get("deadlineReceiptTenders", ""))
        if dl:
            try:
                deadline = datetime.fromisoformat(str(dl).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Published
        published = None
        pd = notice.get("publicationDate", notice.get("datePublished", ""))
        if pd:
            try:
                published = datetime.fromisoformat(str(pd).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Country
        country = ""
        country_data = notice.get("country", notice.get("countryCode", ""))
        if isinstance(country_data, dict):
            country = country_data.get("en", country_data.get("name", ""))
        elif isinstance(country_data, str):
            country = country_data

        # CPV
        cpv_codes = []
        cpv_data = notice.get("cpvCodes", notice.get("cpv", []))
        if isinstance(cpv_data, list):
            for c in cpv_data:
                if isinstance(c, dict):
                    cpv_codes.append(c.get("code", c.get("id", "")))
                elif isinstance(c, str):
                    cpv_codes.append(c)
        elif isinstance(cpv_data, str):
            cpv_codes.append(cpv_data)

        url = TED_NOTICE_URL.format(notice_id=notice_id)

        return Tender(
            source="ted",
            tender_id=str(notice_id),
            title=title,
            description=description[:2000] if description else "",
            buyer=buyer,
            budget=budget,
            currency=currency,
            deadline=deadline,
            published=published,
            url=url,
            cpv_codes=cpv_codes,
            country=country,
            status="active",
        )
    except Exception as e:
        logger.error(f"Error parsing TED notice: {e}")
        return None
