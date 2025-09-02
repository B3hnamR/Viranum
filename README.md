# Numiran Telegram Bot

Dockerized, async, i18n-enabled Telegram bot to purchase virtual numbers via Numberland API.

## Quick Start

1) Copy env and set secrets:

```
cp .env.example .env
# edit .env and set BOT_TOKEN, NUMBERLAND_API_KEY
```

2) Build and run:

```
docker compose build
docker compose up -d
```

3) Logs:

```
docker compose logs -f bot
```

4) Open Telegram and send /start to your bot.

## Tech
- Python 3.11, Aiogram 3, httpx
- PostgreSQL, Redis (compose)
- i18n (fa/en/ru)

## Roadmap
See ROADMAP.md for the full architecture, phases, and tasks.
