"""SAM.gov (US Federal) tender scraper."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp

from .base import Tender
from config import SAM_GOV_API_KEY, SEARCH_KEYWORDS_EN, MIN_BUDGET_USD

logger = logging.getLogger(__name__)

SAM_API_URL = "https://api.sam.gov/opportunities/v2/search"
SAM_OPPORTUNITY_URL = "https://sam.gov/opp/{notice_id}/view"

# NAICS codes for advertising/marketing
RELEVANT_NAICS = [
    "541810",  # Advertising Agencies
    "541820",  # Public Relations Agencies
    "541830",  # Media Buying Agencies
    "541840",  # Media Representatives
    "541850",  # Outdoor Advertising
    "541860",  # Direct Mail Advertising
    "541890",  # Other Services Related to Advertising
    "541613",  # Marketing Consulting Services
    "541910",  # Marketing Research
    "512110",  # Motion Picture and Video Production
    "541430",  # Graphic Design Services
]


async def search_sam_gov(
    session: aiohttp.ClientSession,
    days_back: int = 14,
) -> list[Tender]:
    """Search SAM.gov for relevant US federal opportunities."""
    if not SAM_GOV_API_KEY:
        logger.warning("SAM.gov API key not configured — skipping")
        return []

    tenders: list[Tender] = []
    seen_ids: set[str] = set()

    # Search by keywords
    keywords = [
        "advertising agency",
        "marketing services",
        "creative services",
        "communication campaign",
        "branding services",
        "public relations",
        "media buying",
        "digital marketing campaign",
    ]

    for keyword in keywords:
        kw_tenders = await _search_sam_keyword(session, keyword, days_back)
        for t in kw_tenders:
            if t.tender_id not in seen_ids:
                seen_ids.add(t.tender_id)
                tenders.append(t)

    # Search by NAICS codes
    for naics in RELEVANT_NAICS[:5]:
        naics_tenders = await _search_sam_naics(session, naics, days_back)
        for t in naics_tenders:
            if t.tender_id not in seen_ids:
                seen_ids.add(t.tender_id)
                tenders.append(t)

    logger.info(f"SAM.gov: found {len(tenders)} tenders")
    return tenders


async def _search_sam_keyword(
    session: aiohttp.ClientSession,
    keyword: str,
    days_back: int,
) -> list[Tender]:
    """Search SAM.gov by keyword."""
    tenders = []
    posted_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%m/%d/%Y")
    posted_to = datetime.now(timezone.utc).strftime("%m/%d/%Y")

    try:
        params = {
            "api_key": SAM_GOV_API_KEY,
            "q": keyword,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": 25,
            "offset": 0,
            "status": "active",
        }
        async with session.get(
            SAM_API_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                logger.warning(f"SAM.gov search '{keyword}': HTTP {resp.status}")
                return tenders
            data = await resp.json()
            opportunities = data.get("opportunitiesData", [])
            for opp in opportunities:
                tender = _parse_sam_opportunity(opp)
                if tender:
                    tenders.append(tender)
    except Exception as e:
        logger.error(f"SAM.gov search error ('{keyword}'): {e}")

    return tenders


async def _search_sam_naics(
    session: aiohttp.ClientSession,
    naics: str,
    days_back: int,
) -> list[Tender]:
    """Search SAM.gov by NAICS code."""
    tenders = []
    posted_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%m/%d/%Y")
    posted_to = datetime.now(timezone.utc).strftime("%m/%d/%Y")

    try:
        params = {
            "api_key": SAM_GOV_API_KEY,
            "ncode": naics,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": 25,
            "offset": 0,
            "status": "active",
        }
        async with session.get(
            SAM_API_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                return tenders
            data = await resp.json()
            opportunities = data.get("opportunitiesData", [])
            for opp in opportunities:
                tender = _parse_sam_opportunity(opp)
                if tender:
                    tenders.append(tender)
    except Exception as e:
        logger.error(f"SAM.gov NAICS search error ({naics}): {e}")

    return tenders


def _parse_sam_opportunity(opp: dict) -> Optional[Tender]:
    """Parse a SAM.gov opportunity into a Tender."""
    try:
        notice_id = opp.get("noticeId", opp.get("opportunityId", ""))
        title = opp.get("title", "")
        description = opp.get("description", opp.get("organizationInfo", {}).get("description", ""))

        # Budget / award
        budget = None
        award = opp.get("award", {})
        if award and award.get("amount"):
            budget = float(award["amount"])
        elif opp.get("estimatedValue"):
            budget = float(opp["estimatedValue"])

        if budget is not None and budget < MIN_BUDGET_USD:
            return None

        # Buyer
        buyer = ""
        org = opp.get("fullParentPathName", opp.get("department", ""))
        if not org:
            org_info = opp.get("organizationInfo", {})
            buyer = org_info.get("name", "")
        else:
            buyer = org

        # Deadline
        deadline = None
        dl = opp.get("responseDeadLine", opp.get("closeDateFormatted", ""))
        if dl:
            try:
                deadline = datetime.fromisoformat(str(dl).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                try:
                    deadline = datetime.strptime(str(dl), "%m/%d/%Y")
                except (ValueError, TypeError):
                    pass

        # Published
        published = None
        pd = opp.get("postedDate", "")
        if pd:
            try:
                published = datetime.fromisoformat(str(pd).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        url = SAM_OPPORTUNITY_URL.format(notice_id=notice_id) if notice_id else ""

        return Tender(
            source="sam_gov",
            tender_id=str(notice_id),
            title=title,
            description=description[:2000] if description else "",
            buyer=buyer,
            budget=budget,
            currency="USD",
            deadline=deadline,
            published=published,
            url=url,
            country="USA",
            status="active",
        )
    except Exception as e:
        logger.error(f"Error parsing SAM.gov opportunity: {e}")
        return None
