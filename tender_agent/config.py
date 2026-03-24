"""Configuration for Rockets tender search agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Claude API ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- SAM.gov ---
SAM_GOV_API_KEY = os.getenv("SAM_GOV_API_KEY", "")

# --- Search parameters ---
MIN_BUDGET_UAH = 1_000_000  # 1M UAH minimum
MIN_BUDGET_EUR = 25_000     # ~equivalent for EU tenders
MIN_BUDGET_USD = 25_000     # ~equivalent for US/UN tenders

# --- Search schedule ---
SEARCH_INTERVAL_HOURS = 6  # Run search every 6 hours

# --- Agency profile for relevance scoring ---
AGENCY_PROFILE = """
Rockets. Growth R&D — креативна маркетингова агенція (Україна, Київ).

ПОСЛУГИ:
- Маркетингові та комунікаційні стратегії
- Запуск рекламних кампаній (digital, ATL, BTL, 360)
- Брендинг та ребрендинг (створення нових брендів)
- Креативні рішення та концепції
- Споживацький досвід (consumer experience)
- PR та комунікації
- Медіа-планування та закупівля
- Соціальні медіа та контент
- Виробництво відео/фото контенту
- Дослідження та аналітика ринку

ДОСВІД:
- 10 років на ринку (з 2016)
- 70+ проєктів національного масштабу
- 2 золоті нагороди Effie Awards Europe
- Масштабування проєктів на закордонні ринки

КЛІЄНТИ:
UNICEF, USAID (DAI), ДСНС, Bolt, Юрія-Фарм, Bacardi-Martini, Приватбанк, Roshen, МХП

СЕКТОРИ ДОСВІДУ:
- FMCG, фармацевтика, фінанси/банкінг
- Технології, транспорт/мобільність
- Державний сектор, міжнародні організації
- Соціальні та гуманітарні проєкти
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
    "ребрендинг",
    "PR послуги",
    "медіа планування",
    "медіа закупівля",
    "соціальні медіа",
    "SMM",
    "digital маркетинг",
    "виробництво відео",
    "виробництво контенту",
    "інформаційна кампанія",
    "комунікаційна кампанія",
    "креативна концепція",
    "просування бренду",
]

SEARCH_KEYWORDS_EN = [
    "advertising services",
    "marketing services",
    "advertising campaign",
    "marketing strategy",
    "communication strategy",
    "creative services",
    "branding",
    "rebranding",
    "PR services",
    "public relations",
    "media planning",
    "media buying",
    "social media management",
    "digital marketing",
    "video production",
    "content production",
    "information campaign",
    "communication campaign",
    "creative concept",
    "brand promotion",
    "brand awareness",
    "creative agency",
]

# CPV codes relevant for marketing/advertising
# (Common Procurement Vocabulary — used in Prozorro and TED)
RELEVANT_CPV_CODES = [
    "79340000",  # Advertising and marketing services
    "79341000",  # Advertising services
    "79341100",  # Advertising consultancy
    "79341200",  # Advertising management
    "79341400",  # Advertising campaign services
    "79342000",  # Marketing services
    "79342100",  # Direct marketing services
    "79342200",  # Promotional services
    "79342300",  # Customer services (consumer-oriented)
    "79340000",  # Advertising and marketing
    "79416000",  # Public relations services
    "79416100",  # Public relations management
    "79416200",  # Public relations consultancy
    "79413000",  # Marketing consultancy
    "79822500",  # Graphic design services
    "79956000",  # Fair and exhibition organisation services
    "92111200",  # Advertising film production
    "92111210",  # Advertising film production services
    "22462000",  # Promotional material
    "79800000",  # Printing and related services
    "79821000",  # Print finishing services
    "79824000",  # Printing and distribution services
    "92110000",  # Motion picture and video production
    "72400000",  # Internet services
    "79000000",  # Business services
]
