"""Configuration for Rockets tender search agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Claude API (for AI relevance scoring) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- Search parameters ---
MIN_BUDGET_UAH = 100_000  # Minimum budget in UAH
MIN_BUDGET_EUR = 5_000
MIN_BUDGET_USD = 5_000

# --- Agency profile for relevance scoring ---
AGENCY_PROFILE = """
Rockets. Growth R&D (ТОВ ПУНКТХАУЗ) — креативна маркетингова агенція (Україна, Київ).

ПОСЛУГИ:
- Маркетингові та комунікаційні стратегії
- Запуск рекламних кампаній (digital, ATL, BTL, 360)
- Брендинг та ребрендинг
- Креативні рішення та концепції
- PR та комунікації
- Медіа-планування та закупівля
- Соціальні медіа (SMM) та контент
- Виробництво відео/фото контенту
- Social marketing, behavior change
- Awareness кампанії

КЛІЄНТИ:
UNICEF, USAID, ДСНС, Bolt, ПриватБанк, МОН, Міністерство цифрової трансформації, Roshen, МХП

НАГОРОДИ: 2 золоті Effie Awards Europe
"""

# --- Search keywords ---
SEARCH_KEYWORDS_UA = [
    "рекламні послуги",
    "маркетингові послуги",
    "рекламна кампанія",
    "маркетингова стратегія",
    "комунікаційна стратегія",
    "креативні послуги",
    "брендинг",
    "PR послуги",
    "медіа планування",
    "соціальні медіа",
    "SMM",
    "digital маркетинг",
    "виробництво відео",
    "виробництво контенту",
    "інформаційна кампанія",
    "комунікаційна кампанія",
    "креативна концепція",
    "просування",
    "awareness",
    "social marketing",
    "behavior change",
    "продакшн",
]

SEARCH_KEYWORDS_EN = [
    "advertising services",
    "marketing services",
    "advertising campaign",
    "communication strategy",
    "creative services",
    "branding",
    "PR services",
    "public relations",
    "media planning",
    "social media management",
    "digital marketing",
    "video production",
    "content production",
    "information campaign",
    "communication campaign",
    "awareness campaign",
    "social marketing",
    "behavior change",
    "creative agency",
]

# CPV codes relevant for marketing/advertising
RELEVANT_CPV_CODES = [
    "79340000",  # Advertising and marketing services
    "79341000",  # Advertising services
    "79341100",  # Advertising consultancy
    "79341200",  # Advertising management
    "79341400",  # Advertising campaign services
    "79342000",  # Marketing services
    "79342100",  # Direct marketing services
    "79342200",  # Promotional services
    "79416000",  # Public relations services
    "79416100",  # Public relations management
    "79413000",  # Marketing consultancy
    "79822500",  # Graphic design services
    "92111200",  # Advertising film production
    "22462000",  # Promotional material
    "92110000",  # Motion picture and video production
]
