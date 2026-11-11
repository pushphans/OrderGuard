# OrderGuard – Main Backend

The core commerce foundation of OrderGuard: **user auth** and the **product
catalog** (with stock as the source of record). It also exposes an internal,
service-to-service API that the [AI microservice](../OrderGuard-AI-Microservice/)
uses for catalog reads and stock writes.

> Cart and order ownership lives in the AI microservice. This service is kept
> lean: identity + catalog.

## Features

- **Auth** – register / login / refresh-token with Argon2 password hashing,
  short-lived HS256 JWT access tokens, and rotating refresh tokens stored server-side
- **Products** – public catalog browsing; create / update / delete protected
  by auth and ownership checks (`403` for outsiders, `404` to hide existence)
- **Internal S2S API** – `/internal/products/decrement-stock` atomically
  decrements stock for a batch of products; guarded by a shared service secret
  (`X-Service-Token` header)
- **Rate limiting** – every endpoint is throttled per-IP with SlowAPI
- **Retries** – write paths use Tenacity to automatically retry transient
  database errors with exponential backoff; the engine uses `pool_pre_ping`

## Tech Stack

| Layer      | Choice                                   |
|------------|------------------------------------------|
| Framework  | FastAPI (async)                          |
| Database   | PostgreSQL via SQLAlchemy 2 (asyncpg)    |
| Migrations | Alembic                                  |
| Auth       | PyJWT + Argon2 (pwdlib)                  |
| Resilience | SlowAPI (rate limits) + Tenacity (retry) |
| Tooling    | uv (env / deps / locking)                |

## Project Structure

```
.
├── alembic.ini
├── migrations/                 # Alembic environment + versioned migrations
├── requirements.txt
├── src/
│   └── orderguard/
│       ├── main.py             # App factory, exception handlers, router wiring
│       ├── core/
│       │   ├── config.py       # Pydantic settings (.env)
│       │   ├── db.py           # Async engine, session factory, Base
│       │   ├── enums.py        # Shared enums (OrderStatus)
│       │   ├── errors.py       # Domain exceptions
│       │   ├── limiter.py      # SlowAPI limiter instance
│       │   └── retry.py        # Tenacity db_retry decorator
│       ├── auth/               # register / login / refresh + get_user dependency
│       ├── products/           # Product model / schema / service / router
│       └── internal/           # Service-to-service API (stock writes)
└── uv.lock
```

Each business module follows the same layering: **model → schema → service → router**.

## Getting Started

### Prerequisites

- Python 3.14+
- PostgreSQL running on `localhost:5432`
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
# 1. install dependencies
uv sync

# 2. configure environment
cp .env.example .env      # set JWT_SECRET_KEY and SERVICE_SECRET

# 3. create the database
createdb order_guard      # or: psql -c "CREATE DATABASE order_guard;"

# 4. apply migrations
uv run alembic upgrade head

# 5. run the API
uv run uvicorn orderguard.main:app --app-dir src --port 8000 --reload
```

The OpenAPI docs are available at `http://127.0.0.1:8000/docs`.

### Environment Variables

| Variable                          | Description                    | Example                                        |
|-----------------------------------|--------------------------------|------------------------------------------------|
| `DATABASE_URL`                    | Async PostgreSQL connection    | `postgresql+asyncpg://postgres:root@localhost:5432/order_guard` |
| `ACCESS_TOKEN_EXPIRY_IN_MINUTES`  | Access token lifetime          | `30`                                           |
| `REFRESH_TOKEN_EXPIRY_IN_DAYS`    | Refresh token lifetime         | `7`                                            |
| `JWT_SECRET_KEY`                  | HS256 signing key (**shared with the AI service**) | `<random 64+ chars>` |
| `ALGORITHM`                       | JWT algorithm                  | `HS256`                                        |
| `SERVICE_SECRET`                  | Shared S2S secret (**shared with the AI service**) | `<random 32+ chars>` |

`.env` is gitignored; never commit it.

## API Endpoints

### Auth (`/auth`)

| Method | Path                | Auth | Limit  | Description                  |
|--------|---------------------|------|--------|------------------------------|
| POST   | `/auth/register`    | –    | 10/min | Create an account            |
| POST   | `/auth/login`       | –    | 10/min | Get access + refresh tokens  |
| POST   | `/auth/refresh-token`| –   | 10/min | Rotate refresh, new access   |

### Products (`/products`)

| Method  | Path                 | Auth   | Limit  | Description                     |
|---------|----------------------|--------|--------|---------------------------------|
| GET     | `/products`          | –      | 60/min | List/search catalog (paginated) |
| GET     | `/products/{id}`     | –      | 60/min | Product detail                  |
| POST    | `/products`          | Bearer | 10/min | Create product (owned by caller)|
| PUT     | `/products/{id}`     | Bearer | 10/min | Update own product (`403` otherwise) |
| DELETE  | `/products/{id}`     | Bearer | 10/min | Delete own product              |

### Internal (`/internal`) – service-to-service

| Method | Path                                   | Auth            | Limit  | Description                                   |
|--------|----------------------------------------|-----------------|--------|-----------------------------------------------|
| POST   | `/internal/products/decrement-stock`   | `X-Service-Token` | 60/min | Atomically decrement stock for a batch of products (`404` unknown, `409` insufficient, `403` bad secret) |

Not intended for end users; authenticated by the shared `SERVICE_SECRET`.

## Design Notes

- **Stock is the source of record here.** The AI service reads product data
  over HTTP and writes stock through the internal endpoint only.
- **The stock decrement is a single atomic batch**: one conditional
  `UPDATE ... WHERE stock_quantity >= quantity` per product, all-or-nothing.
  This is what lets the AI service place orders safely and lets concurrent
  orders be serialized.
- **Public product reads** are open to any caller (catalog browsing); the
  AI microservice uses them for cart/order tooling.
- **Retries are applied to write paths** via `@db_retry`: 3 attempts,
  exponential backoff, on transient SQLAlchemy `OperationalError` /
  `InterfaceError`, with `pool_pre_ping` so pooled connections are
  health-checked before reuse.

## Roadmap

- [ ] Test suite + CI
- [ ] Admin / moderation surface for the catalog
