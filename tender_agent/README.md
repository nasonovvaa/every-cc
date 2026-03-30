# 🚀 Rockets Tender Agent

Щоденний моніторинг тендерів для креативної маркетингової агенції Rockets. Growth R&D (ТОВ ПУНКТХАУЗ).

## Джерела моніторингу

| Платформа | Регіон | Метод |
|-----------|--------|-------|
| **SmartTender.biz** | 🇺🇦 Україна | Scraping |
| **UNGM.org** | 🇺🇳 Міжнародний | API + scraping |
| **GIZ Ukraine** | 🇩🇪 Міжнародний | Scraping |
| **E-Tender.ua** | 🇺🇦 Україна | Scraping |

## Як це працює

1. **Парсинг** — Щодня о 9:00 за Києвом агент перевіряє всі 4 сайти
2. **Фільтрація** — Відбирає тендери за ключовими словами: реклама, комунікації, PR, SMM, кампанії, awareness, соціальний маркетинг, медіа, брендинг, продакшн, контент
3. **AI оцінка** — Claude Haiku оцінює релевантність кожного тендера (0-100)
4. **Дедуплікація** — SQLite база зберігає надіслані тендери, щоб не дублювати
5. **Telegram дайджест** — Нові тендери надсилаються у форматі:

```
🆕 НОВИЙ ТЕНДЕР
📌 Назва: ...
🏢 Замовник: ...
💰 Бюджет: ...
⏰ Дедлайн: ...
🔗 Посилання: ...
```

## Швидкий старт

### 1. Встановлення

```bash
cd tender_agent
pip install -r requirements.txt
```

### 2. Налаштування

```bash
cp .env.example .env
```

Заповніть `.env`:

```env
TELEGRAM_BOT_TOKEN=...    # Створити бота через @BotFather
TELEGRAM_CHAT_ID=...      # Отримати через @userinfobot
ANTHROPIC_API_KEY=...     # Опціонально — для AI оцінки релевантності
```

**Як отримати Telegram Chat ID:**
1. Напишіть боту @userinfobot або @getmyid_bot
2. Він покаже ваш Chat ID

### 3. Запуск

```bash
# Одноразовий пошук (як з GitHub Actions)
python main.py --once

# Постійна робота з Telegram ботом
python main.py
```

### 4. Автоматизація (GitHub Actions)

Вже налаштований workflow `.github/workflows/tender-monitor.yml`.

Додайте секрети в Settings → Secrets → Actions:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `ANTHROPIC_API_KEY` (опціонально)

Агент запускатиметься щодня о 9:00 за Києвом автоматично.

### 5. Docker (альтернатива)

```bash
docker compose up -d
```

## Telegram команди

| Команда | Опис |
|---------|------|
| `/start` | Привітання та інфо |
| `/search` | Запустити пошук вручну |
| `/status` | Статус агента |
| `/help` | Довідка |

## Налаштування

Параметри у `config.py`:
- `MIN_BUDGET_UAH` — мінімальний бюджет
- `SEARCH_KEYWORDS_UA` / `SEARCH_KEYWORDS_EN` — ключові слова пошуку
- `RELEVANT_CPV_CODES` — CPV коди для фільтрації
- `AGENCY_PROFILE` — профіль агенції для AI оцінки
