# Changelog

All notable changes to this project will be documented in this file.
This project follows a simplified Keep a Changelog style with semantic versions.


## [0.2.1] - 2025-09-02
### Added
- Internal wallet (Redis-based): balance storage, transaction history, credit/debit helpers.
- Manual top-up flow with admin approval:
  - User requests top-up amount; request persisted in Redis (wallet:topup:<id>),
  - Admins (from ADMIN_IDS) receive inline Approve/Reject actions,
  - On approval, user wallet is credited and notified; on rejection, informed accordingly.
- Wallet UI in bot:
  - Wallet main view shows internal balance and offers actions: Increase balance, History, Back.
  - History view lists last 10 transactions (credit/debit) for transparency.
- /balance command to quickly verify connectivity to Numberland (fetch panel balance).
- u.sh deployment helper script to: git fetch/checkout/pull, docker compose build/up, and tail logs.

### Notes
- Wallet is currently in Redis for speed and simplicity (MVP). Persisting to PostgreSQL will be introduced next with models/migrations.
- Purchase flow does not yet debit the internal wallet. This will be wired in a subsequent release to enforce pre-paid purchases and handle refunds automatically.


## [0.2.0] - 2025-09-02
### Added
- Numberland API client (async, httpx) with:
  - Endpoints: balance, getinfo, getnum, checkstatus, cancelnumber, bannumber, repeat, closenumber,
    getcountry, getservice, spnumberslist, spnumberstree, getspnumber, myspnumbers.
  - Error mapping for negative RESULT codes, timeouts, retry with exponential backoff, and HTTP error handling.
- Pricing service: markup with rounding and minimum profit policy.
- Temporary-number purchase flow (end-to-end):
  - Select service (pagination) -> select country (pagination) -> select operator (1..4, any, min),
  - Quote via getinfo with final price calculation, confirm purchase -> getnum,
  - Order message with number/price/time/repeat, background polling checkstatus,
  - Control buttons: Cancel, Repeat, Close, Refresh,
  - Multi-language messages (FA/EN/RU).

### Notes
- Polling interval set to 4s with automatic stop on code received, canceled, banned, or completed.
- i18n implemented as an in-memory stub for MVP; will be migrated to gettext .po files later.


## [0.1.0] - 2025-09-02
### Added
- Project scaffolding and documentation:
  - api.md: structured summary of Numberland API.
  - ROADMAP.md: architecture, folder structure, phases, Docker plan, flows, pricing rules, i18n strategy.
  - README.md: quick start with Docker instructions.
- Infrastructure:
  - docker-compose.yml: services for bot, Postgres, Redis with healthchecks and volumes.
  - infra/Dockerfile: Python 3.11-slim base, non-root user, requirements install.
  - infra/requirements.txt: aiogram, httpx, SQLAlchemy, Alembic, asyncpg, redis, loguru, etc.
  - .env.example: environment template (BOT_TOKEN, NUMBERLAND_API_KEY, DB/REDIS DSN, pricing defaults).
- Application skeleton:
  - src/app/main.py: entrypoint with main menu and language settings (FA/EN/RU).
  - src/app/config.py: pydantic settings.
  - src/app/i18n.py: translation stub and keys for UI text.
  - src/app/utils/logger.py: Loguru setup.
  - src/app/utils/enums.py: number status enum.
  - src/app/db.py: async engine/session factory for future DB usage.

### Notes
- Initial mode uses long polling; webhook can be added in future phases.
- Next steps outlined in ROADMAP: DB models/migrations, caching, wallet enforcement, permanent numbers, tests/CI.


---

Summary:
```
Bootstrap Dockerized aiogram bot with Numberland API integration, add full temporary-number flow, Redis-backed internal wallet with manual top-up (admin approval), and deployment helper u.sh. Docs included (api.md, ROADMAP.md, README.md).
```

Description:
```
- 0.1.0: Initial scaffolding (Docker, compose, requirements, env), app skeleton (main/config/i18n/logger/db), and docs.
- 0.2.0: Implement Numberland client, pricing, and end-to-end temporary-number purchase flow with status polling and controls.
- 0.2.1: Add internal wallet (Redis), manual top-up with admin approval, wallet UI (balance/history), /balance command, and u.sh script for pull/rebuild/restart/logs.
```