# ByStars

Телеграм-бот и FastAPI-сервис для покупки Telegram Stars и Telegram Premium через Fragment/TON.

## Что делает проект
- Запускает Telegram-бота (aiogram) для пользователей.
- Поднимает внутренний API (`/v1/stars/*`, `/v1/premium/*`) для операций покупки.
- Хранит пользователей, заказы и платежные инвойсы в PostgreSQL.
- Отправляет транзакции через TON-кошелек.

## Стек
- Python 3.13
- aiogram
- FastAPI + uvicorn
- PostgreSQL + asyncpg
- httpx
- tonutils / pytoniq-core

## Структура
- `main.py` — запускает и бота, и API вместе.
- `bot_main.py` — Telegram-бот.
- `fragment_api/frag_api_main.py` — запуск FastAPI.
- `src/` — бизнес-логика API и интеграции с Fragment/TON.
- `db.py` — слой БД и миграция таблиц при старте.
- `.env.example` — пример конфигурации.

## Требования
- Python 3.13+
- PostgreSQL 13+
- Созданные ключи/секреты из `.env.example`

## Установка
1. Клонировать репозиторий:
```bash
git clone <https://github.com/artemspt/telegram_buy_stars-premium>
cd ByStars
```

2. Создать виртуальное окружение и установить зависимости:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Создать `.env` на основе примера:
```bash
cp .env.example .env
```

4. Заполнить `.env` реальными значениями.

## Запуск
### Вариант 1: всё сразу (рекомендуется)
```bash
python3 main.py
```

### Вариант 2: по отдельности
Только API:
```bash
python3 fragment_api/frag_api_main.py
```

Только бот:
```bash
python3 bot_main.py
```

## Как пользоваться
### Для пользователя бота
- Открыть бота в Telegram.
- Нажать `/start`.
- Выбрать покупку Stars или Premium.
- Указать username получателя и количество/срок.

### Для администратора
- `ADMIN_ID` даёт доступ к кнопке «Админ панель».
- Команда `/paid <memo> <tx_hash> <amount_nano>` помечает инвойс как оплаченный.

## API (кратко)
Базовый префикс: `/v1`

### Купить Stars
`POST /v1/stars/buy`

Пример:
```bash
curl -X POST 'http://127.0.0.1:8000/v1/stars/buy' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_KEY>' \
  -d '{"username":"durov","quantity":50}'
```

### Купить Premium
`POST /v1/premium/buy`

Пример:
```bash
curl -X POST 'http://127.0.0.1:8000/v1/premium/buy' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_KEY>' \
  -d '{"username":"durov","months":"3"}'
```

## Важно по безопасности
- Не коммитьте `.env` и `fragment_api/fragment_session.json`.
- Используйте отдельные ключи для dev/prod.
- Для production выключайте `SERVER__RELOAD` (`false`).

## Типичные проблемы
- `BOT_TOKEN is not set` — не заполнен `BOT_TOKEN` в `.env`.
- Ошибки БД — проверьте `DB_*` и доступ к PostgreSQL.
- `Unauthorized` в API — проверьте `API_KEY` и заголовок `Authorization`.

---

# ByStars (English)

Telegram bot + FastAPI service for purchasing Telegram Stars and Telegram Premium via Fragment/TON.

## What This Project Does
- Runs a Telegram bot (aiogram) for end users.
- Exposes internal API endpoints (`/v1/stars/*`, `/v1/premium/*`) for purchase operations.
- Stores users, orders, and payment invoices in PostgreSQL.
- Sends transactions through a TON wallet.

## Stack
- Python 3.13
- aiogram
- FastAPI + uvicorn
- PostgreSQL + asyncpg
- httpx
- tonutils / pytoniq-core

## Project Structure
- `main.py` - starts both bot and API together.
- `bot_main.py` - Telegram bot.
- `fragment_api/frag_api_main.py` - FastAPI runner.
- `src/` - API business logic and Fragment/TON integrations.
- `db.py` - database layer and startup table initialization.
- `.env.example` - configuration template.

## Requirements
- Python 3.13+
- PostgreSQL 13+
- Valid secrets/keys from `.env.example`

## Installation
1. Clone repository:
```bash
git clone <your-repo-url>
cd ByStars
```

2. Create virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Create `.env` from template:
```bash
cp .env.example .env
```

4. Fill `.env` with real values.

## Run
### Option 1: run everything (recommended)
```bash
python3 main.py
```

### Option 2: run separately
API only:
```bash
python3 fragment_api/frag_api_main.py
```

Bot only:
```bash
python3 bot_main.py
```

## Usage
### For bot users
- Open the bot in Telegram.
- Run `/start`.
- Choose Stars or Premium purchase.
- Enter recipient username and quantity/months.

### For admin
- `ADMIN_ID` grants access to the "Admin Panel" button.
- `/paid <memo> <tx_hash> <amount_nano>` marks invoice as paid.

## API (Short)
Base prefix: `/v1`

### Buy Stars
`POST /v1/stars/buy`

Example:
```bash
curl -X POST 'http://127.0.0.1:8000/v1/stars/buy' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_KEY>' \
  -d '{"username":"durov","quantity":50}'
```

### Buy Premium
`POST /v1/premium/buy`

Example:
```bash
curl -X POST 'http://127.0.0.1:8000/v1/premium/buy' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_KEY>' \
  -d '{"username":"durov","months":"3"}'
```

## Security Notes
- Do not commit `.env` and `fragment_api/fragment_session.json`.
- Use separate secrets for dev/prod.
- Disable `SERVER__RELOAD` (`false`) in production.

## Common Issues
- `BOT_TOKEN is not set` - `BOT_TOKEN` is missing in `.env`.
- DB errors - verify `DB_*` values and PostgreSQL access.
  - `Unauthorized` in API - check `API_KEY` and `Authorization` header.

## Contact information:
  telegram: @sptsupport