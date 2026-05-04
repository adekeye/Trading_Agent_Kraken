# Kraken Trading Agent

A safety-first web application that turns natural-language commands like
**"Buy 1000 XRP at 0.55"** into Kraken **limit orders**, with explicit
preview & confirmation, dry-run mode, and a kill switch.

> ⚠️ **Crypto only.** This app supports Kraken-listed crypto pairs. It will
> reject anything that looks like a stock, market order, or vague instruction.

## Architecture

```
Trading_Agent_Kraken/
├── backend/                    # FastAPI service
│   ├── app/
│   │   ├── main.py             # app entrypoint, CORS, rate limit, routers
│   │   ├── config.py           # pydantic settings from env
│   │   ├── database.py         # SQLAlchemy engine, session, Base
│   │   ├── models.py           # User, KrakenCredential, UserSettings,
│   │   │                       # AuditLog, OrderRecord, PendingConfirmation
│   │   ├── schemas.py          # pydantic request/response schemas
│   │   ├── auth.py             # bcrypt, JWT, current_user dep
│   │   ├── crypto_utils.py     # Fernet encrypt/decrypt for API keys
│   │   ├── kraken_client.py    # async Kraken REST client (signed)
│   │   ├── command_parser.py   # NL → ParsedCommand
│   │   ├── risk_engine.py      # safety rules
│   │   ├── order_service.py    # preview + confirm + dry-run + audit
│   │   ├── audit_logger.py     # append-only audit, secret scrubber
│   │   └── routers/            # /auth, /kraken, /commands, /audit-logs
│   ├── tests/                  # parser, risk engine, Kraken mock, smoke
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/                   # Next.js 14 (App Router) + TypeScript
│   ├── app/
│   │   ├── layout.tsx, page.tsx (Trade)
│   │   ├── login/, register/, connect/
│   │   ├── balances/, orders/, history/, audit/, settings/
│   │   └── globals.css
│   ├── components/             # Nav, OrderPreviewCard, ConfirmationModal
│   ├── lib/                    # api client, types
│   ├── package.json, tsconfig.json, next.config.js
│   └── Dockerfile
├── docker-compose.yml          # Postgres + backend + frontend
├── .env.example
├── .gitignore
└── README.md (this file)
```

## Quick start (local, without Docker)

### 1. Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Copy env and edit
cp ../.env.example ../.env
# Generate a real Fernet key (recommended)
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# paste into .env as ENCRYPTION_KEY=...

.venv/bin/uvicorn app.main:app --reload --port 8000
```

The API will be at <http://localhost:8000>; OpenAPI docs at `/docs`.

### 2. Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Visit <http://localhost:3000>.

### 3. Use the app

1. Register an account → redirected to **Connect Kraken**.
2. Paste your Kraken API **key + secret** (need at least *Query Funds* and
   *Modify Orders* permissions).
3. Open **Settings**. By default the app is in **DRY-RUN** mode and the global
   trading switch is on. **Leave dry-run on** until you're confident.
4. Go to **Trade** and try a command.

## Quick start (Docker Compose)

```bash
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET and ENCRYPTION_KEY.
# Set DATABASE_URL=postgresql+psycopg://kta:kta@db:5432/kta in .env (or rely on the
# default override in docker-compose.yml).

docker compose up --build
```

The app will be at <http://localhost:3000> (Postgres at `localhost:5432`).

## Order flow (10 steps)

```
1. User types text command
2. POST /commands/parse        → backend parses to a ParsedCommand
3. Risk engine validates       (kill switch, max notional, supported asset…)
4. POST /commands/preview      → returns OrderPreview + confirmation_id
5. UI shows preview + warnings (dry-run badge, two-step phrase if needed)
6. User clicks "Confirm Order"
7. Backend re-runs risk checks
8. Either:  Kraken AddOrder(limit)  *OR* dry-run simulated record
9. AuditLog row appended for every step
10. UI shows the success/failure result with Kraken txid
```

## Safety guarantees baked in

| Safeguard                                           | Where                                           |
|-----------------------------------------------------|-------------------------------------------------|
| No order without explicit confirmation              | `/commands/preview` + `/commands/confirm`       |
| Limit orders only — market/stop rejected            | `command_parser.py`, `kraken_client.add_order`  |
| Stocks/equities rejected                            | `command_parser.py` STOCK_KEYWORDS              |
| Vague commands rejected                             | `command_parser.py` VAGUE_PHRASES               |
| Per-user max notional (default $1000)               | `risk_engine.py`                                |
| Two-step phrase for large orders                    | `risk_engine.py` + `order_service.py`           |
| Dry-run mode (default ON)                           | `UserSettings.dry_run`, applied in service      |
| Global kill switch                                  | `UserSettings.trading_enabled`                  |
| Confirmations expire after 120 s                    | `order_service.CONFIRMATION_TTL_SECONDS`        |
| API keys encrypted at rest with Fernet              | `crypto_utils.py`, `KrakenCredential`           |
| API secrets never logged                            | `audit_logger._scrub`                           |
| Append-only audit log per user                      | `models.AuditLog`, written from every step      |
| Rate limit                                          | `slowapi`, configurable via `RATE_LIMIT_*`      |
| Kraken nonce handled per request                    | `KrakenClient._nonce`                           |
| HMAC-SHA512 request signing                         | `KrakenClient._sign`                            |

## Example commands

**Valid (place_order):**

| Command                                  | Result                                       |
|------------------------------------------|----------------------------------------------|
| `Buy 1000 XRP at 0.55`                   | XRPUSD limit buy, 1000 @ 0.55                |
| `Sell 0.05 BTC at 65000`                 | XBTUSD limit sell, 0.05 @ 65000              |
| `Buy $500 worth of ETH at 3100`          | ETHUSD; quantity derived = 500/3100          |
| `sell 2 eth at $4,200`                   | ETHUSD limit sell, 2 @ 4200                  |
| `buy 100 sol @ 150`                      | SOLUSD limit buy, 100 @ 150                  |

**Valid (read-only):**

- `Show my balances`
- `Show open orders`
- `Cancel order OABC-123`

**Rejected (with reason):**

| Command                            | Reason                                          |
|------------------------------------|-------------------------------------------------|
| `Buy Tesla stock`                  | stocks not supported                            |
| `Market buy BTC`                   | only limit orders are supported                 |
| `Buy BTC`                          | missing limit price                             |
| `Sell all my eth at 4000`          | "all" not allowed; specify exact quantity       |
| `Sell 100 SOL if price reaches 180`| conditional orders not supported                |
| `Make me money`                    | command too vague                               |
| `go all in on bitcoin`             | command too vague                               |

## API endpoints

```
POST  /auth/register
POST  /auth/login
GET   /auth/me

POST  /kraken/connect              save & verify API credentials
GET   /kraken/balances
GET   /kraken/pairs                public asset pair info
GET   /kraken/open-orders
GET   /kraken/order-history
POST  /kraken/place-order          (direct; requires confirm:true)
POST  /kraken/cancel-order

POST  /commands/parse              text → ParsedCommand
POST  /commands/preview            text → OrderPreview (creates pending confirmation)
POST  /commands/confirm            confirmation_id → OrderResult (places order)

GET   /audit-logs
GET   /settings
PUT   /settings
```

Interactive docs: <http://localhost:8000/docs>.

## Running tests

```bash
cd backend
.venv/bin/python -m pytest -v
```

Test suites:

- `tests/test_parser.py` — parser intent extraction & rejection rules
- `tests/test_risk_engine.py` — risk decisions (kill switch, caps, two-step)
- `tests/test_kraken_client.py` — Kraken signing & response parsing (respx mock)
- `tests/test_app_boot.py` — full register/login/preview/confirm in dry-run

## Production checklist

Before pointing this at real Kraken keys:

- [ ] Set a strong `JWT_SECRET` and a real Fernet `ENCRYPTION_KEY` in `.env`
- [ ] Switch `DATABASE_URL` to Postgres
- [ ] Set `CORS_ORIGINS` to your real frontend origin
- [ ] Set `APP_ENV=production`
- [ ] Run on HTTPS behind a reverse proxy (TLS terminates there)
- [ ] Tighten `RATE_LIMIT_PER_MINUTE`
- [ ] Use Kraken API keys with the **minimum** scopes you need
- [ ] Keep dry-run mode ON and place small test orders first
- [ ] Audit logs should be exported / shipped to durable storage
- [ ] Add monitoring on `/health` and on rate-limit / 5xx responses

## License

Provided as-is. Trading is your responsibility — review every preview carefully.
