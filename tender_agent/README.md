# 🚀 Rockets Tender Agent

Автоматичний пошук тендерів на рекламні та маркетингові послуги для агенції Rockets. Growth R&D.

## Джерела пошуку

| Платформа | Регіон | Тип |
|-----------|--------|-----|
| **Prozorro** | 🇺🇦 Україна | API |
| **TED** (Tenders Electronic Daily) | 🇪🇺 ЄС | API |
| **UNGM** (UN Global Marketplace) | 🇺🇳 Міжнародний | API + scraping |
| **SAM.gov** | 🇺🇸 США | API |
| **DG Market** | 🌍 Міжнародний | Scraping |
| **Devex** | 🌍 Міжнародний | Scraping |

## Як це працює

1. **Збір** — Агент шукає тендери по ключових словах та CPV кодах (реклама, маркетинг, PR, брендинг)
2. **Фільтрація** — Мінімальний бюджет 1 000 000 грн (або еквівалент в EUR/USD)
3. **AI оцінка** — Claude Haiku аналізує кожен тендер та оцінює релевантність 0-100
4. **Звіт** — Telegram бот надсилає топ тендерів з оцінками та посиланнями

## Швидкий старт

### 1. Встановлення залежностей

```bash
cd tender_agent
pip install -r requirements.txt
```

### 2. Налаштування

Скопіюйте `.env.example` → `.env` та заповніть:

```bash
cp .env.example .env
```

```env
# Обов'язково:
TELEGRAM_BOT_TOKEN=...    # Отримати у @BotFather
TELEGRAM_CHAT_ID=...      # ID чату/групи для повідомлень
ANTHROPIC_API_KEY=...     # API ключ Claude (anthropic.com)

# Опціонально:
SAM_GOV_API_KEY=...       # Для пошуку на SAM.gov (sam.gov/api)
```

**Як отримати Telegram Chat ID:**
1. Створіть бота через @BotFather
2. Надішліть боту будь-яке повідомлення
3. Відкрийте `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Знайдіть `chat.id` у відповіді

### 3. Запуск

```bash
python main.py
```

Агент:
- Одразу запустить перший пошук
- Далі автоматично шукатиме кожні 6 годин
- Telegram бот приймає команди `/search`, `/status`, `/help`

## Telegram команди

| Команда | Опис |
|---------|------|
| `/start` | Привітання та інфо |
| `/search` | Запустити пошук вручну |
| `/status` | Статус агента |
| `/help` | Довідка |

## Налаштування

Основні параметри у `config.py`:

- `MIN_BUDGET_UAH` — мінімальний бюджет (за замовчуванням 1 000 000 грн)
- `SEARCH_INTERVAL_HOURS` — інтервал пошуку (за замовчуванням 6 годин)
- `SEARCH_KEYWORDS_UA` / `SEARCH_KEYWORDS_EN` — ключові слова пошуку
- `RELEVANT_CPV_CODES` — CPV коди для фільтрації

## Без Telegram (консольний режим)

Якщо не вказати `TELEGRAM_BOT_TOKEN`, агент працюватиме у консольному режимі та виводитиме результати у термінал.
