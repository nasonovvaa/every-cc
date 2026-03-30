"""Base tender model and scraper interface."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Tender:
    """Unified tender representation across all platforms."""
    source: str                          # e.g. "prozorro", "ted", "ungm", "sam_gov"
    tender_id: str                       # Unique ID on the platform
    title: str
    description: str
    buyer: str                           # Organization that posted the tender
    budget: Optional[float] = None       # Estimated value
    currency: str = "UAH"
    deadline: Optional[datetime] = None  # Submission deadline
    published: Optional[datetime] = None
    url: str = ""                        # Direct link
    cpv_codes: list[str] = field(default_factory=list)
    country: str = ""
    status: str = ""
    relevance_score: float = 0.0        # 0-100, set by AI scoring
    relevance_reason: str = ""          # AI explanation

    @property
    def budget_display(self) -> str:
        if self.budget is None:
            return "Не вказано"
        if self.currency == "UAH":
            return f"{self.budget:,.0f} грн"
        return f"{self.budget:,.0f} {self.currency}"

    @property
    def deadline_display(self) -> str:
        if self.deadline is None:
            return "Не вказано"
        return self.deadline.strftime("%d.%m.%Y %H:%M")

    def to_telegram_message(self) -> str:
        """Format tender as a Telegram message."""
        stars = "⭐" * min(5, max(1, int(self.relevance_score / 20)))
        source_labels = {
            "smarttender": "🇺🇦 SmartTender.biz",
            "ungm": "🇺🇳 UNGM (UN)",
            "giz": "🇩🇪 GIZ Ukraine",
            "etender": "🇺🇦 E-Tender.ua",
        }
        source_label = source_labels.get(self.source, self.source)

        msg = (
            f"{stars} <b>Релевантність: {self.relevance_score:.0f}/100</b>\n"
            f"📌 <b>{self.title}</b>\n\n"
            f"🏢 {self.buyer}\n"
            f"💰 {self.budget_display}\n"
            f"📅 Дедлайн: {self.deadline_display}\n"
            f"🌐 Джерело: {source_label}\n"
        )
        if self.country:
            msg += f"📍 Країна: {self.country}\n"
        if self.relevance_reason:
            msg += f"\n💡 <i>{self.relevance_reason}</i>\n"
        if self.url:
            msg += f"\n🔗 <a href=\"{self.url}\">Переглянути тендер</a>"
        return msg
