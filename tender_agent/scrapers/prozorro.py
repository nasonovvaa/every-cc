"""Prozorro (Ukraine) tender scraper using the official API."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp

from .base import Tender
from config import SEARCH_KEYWORDS_UA, RELEVANT_CPV_CODES, MIN_BUDGET_UAH

logger = logging.getLogger(__name__)

PROZORRO_API = "https://public.api.openprocurement.org/api/2.5"
PROZORRO_SEARCH_API = "https://prozorro.gov.ua/api/search/tenders"


async def search_prozorro(
    session: aiohttp.ClientSession,
    days_back: int = 7,
) -> list[Tender]:
    """Search Prozorro for relevant tenders."""
    tenders: list[Tender] = []
    seen_ids: set[str] = set()

    # Strategy 1: Search by CPV codes via the search API
    cpv_tenders = await _search_by_cpv(session, days_back)
    for t in cpv_tenders:
        if t.tender_id not in seen_ids:
            seen_ids.add(t.tender_id)
            tenders.append(t)

    # Strategy 2: Search by keywords via the search API
    for keyword in SEARCH_KEYWORDS_UA[:10]:  # Limit to avoid rate limits
        kw_tenders = await _search_by_keyword(session, keyword, days_back)
        for t in kw_tenders:
            if t.tender_id not in seen_ids:
                seen_ids.add(t.tender_id)
                tenders.append(t)
        await asyncio.sleep(0.5)  # Rate limiting

    logger.info(f"Prozorro: found {len(tenders)} tenders")
    return tenders


async def _search_by_cpv(
    session: aiohttp.ClientSession,
    days_back: int,
) -> list[Tender]:
    """Search Prozorro by CPV codes."""
    tenders = []
    date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # Use top-level CPV codes for broader search
    top_cpv = ["79340000", "79341000", "79342000", "79416000", "79413000"]

    for cpv in top_cpv:
        try:
            params = {
                "cpv": cpv,
                "date_modified_from": date_from,
                "status": "active.tendering",
                "page": 1,
                "per_page": 50,
            }
            async with session.get(
                PROZORRO_SEARCH_API, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Prozorro CPV search {cpv}: HTTP {resp.status}")
                    continue
                data = await resp.json()
                items = data if isinstance(data, list) else data.get("data", data.get("items", []))
                for item in items:
                    tender = _parse_prozorro_item(item)
                    if tender and (tender.budget is None or tender.budget >= MIN_BUDGET_UAH):
                        tenders.append(tender)
        except Exception as e:
            logger.error(f"Prozorro CPV search error ({cpv}): {e}")
        await asyncio.sleep(0.3)

    return tenders


async def _search_by_keyword(
    session: aiohttp.ClientSession,
    keyword: str,
    days_back: int,
) -> list[Tender]:
    """Search Prozorro by keyword."""
    tenders = []
    date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    try:
        params = {
            "query": keyword,
            "date_modified_from": date_from,
            "status": "active.tendering",
            "page": 1,
            "per_page": 30,
        }
        async with session.get(
            PROZORRO_SEARCH_API, params=params, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                logger.warning(f"Prozorro keyword search '{keyword}': HTTP {resp.status}")
                return tenders
            data = await resp.json()
            items = data if isinstance(data, list) else data.get("data", data.get("items", []))
            for item in items:
                tender = _parse_prozorro_item(item)
                if tender and (tender.budget is None or tender.budget >= MIN_BUDGET_UAH):
                    tenders.append(tender)
    except Exception as e:
        logger.error(f"Prozorro keyword search error ('{keyword}'): {e}")

    return tenders


def _parse_prozorro_item(item: dict) -> Optional[Tender]:
    """Parse a Prozorro API item into a Tender object."""
    try:
        tender_id = item.get("tenderID", item.get("id", ""))
        title = item.get("title", item.get("title_uk", ""))
        description = item.get("description", item.get("description_uk", ""))

        # Budget
        budget = None
        currency = "UAH"
        value = item.get("value", {})
        if value:
            budget = value.get("amount")
            currency = value.get("currency", "UAH")

        # Buyer
        buyer = ""
        procuring = item.get("procuringEntity", {})
        if procuring:
            buyer = procuring.get("name", procuring.get("name_uk", ""))

        # Deadline
        deadline = None
        tender_period = item.get("tenderPeriod", {})
        if tender_period and tender_period.get("endDate"):
            try:
                deadline = datetime.fromisoformat(
                    tender_period["endDate"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Published date
        published = None
        if item.get("dateCreated"):
            try:
                published = datetime.fromisoformat(
                    item["dateCreated"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # CPV codes
        cpv_codes = []
        for classification in [item.get("classification", {})] + item.get("additionalClassifications", []):
            if classification and classification.get("id"):
                cpv_codes.append(classification["id"])

        # URL
        url = f"https://prozorro.gov.ua/tender/{tender_id}" if tender_id else ""

        return Tender(
            source="prozorro",
            tender_id=tender_id,
            title=title,
            description=description[:2000] if description else "",
            buyer=buyer,
            budget=budget,
            currency=currency,
            deadline=deadline,
            published=published,
            url=url,
            cpv_codes=cpv_codes,
            country="Україна",
            status=item.get("status", ""),
        )
    except Exception as e:
        logger.error(f"Error parsing Prozorro item: {e}")
        return None
