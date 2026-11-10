# OrderGuard

A simple, portfolio-grade e-commerce backend built as a monolithic FastAPI service. It covers the core commerce flow: **products → cart → orders**, secured by JWT authentication, with per-endpoint rate limiting and fault-tolerant write paths.

> An AI module will be added later as a separate microservice; this repository is intentionally kept lean and monolithic until then.

## Features

- **Products** – public catalog browsing, with create / update / delete protected by auth and ownership checks
- **Cart** – per-user cart with quantity merging and live stock validation
- **Orders** – place an order from the cart in a single atomic step: total computation, stock decrement, order-item snapshotting, and cart clearing all happen in one transaction
- **Auth** – register / login / refresh-token with Argon2 password hashing, short-lived JWT access tokens, and rotating refresh tokens stored server-side
- **Ownership enforcement** – every mutating CRUD path verifies the caller owns the resource (`403` for outsiders, `404` to hide existence of others' orders)
- **Rate limiting** – every endpoint is throttled per-IP with SlowAPI
- **Retries** – state-changing (write) endpoints use Tenacity to automatically retry transient database errors with exponential backoff

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
│       ├── cart/               # Cart item model / schema / service / router
│       └── orders/             # Order + order item models, service, router
└── uv.lock
```

Each business module follows the same layering: **model → schema → service → router**, mirroring the structure of sibling projects in this codebase.

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
cp .env.example .env      # or create .env manually (see below)

# 3. create the database
createdb order_guard      # or: psql -c "CREATE DATABASE order_guard;"

# 4. apply migrations
uv run alembic upgrade head

# 5. run the API
uv run uvicorn orderguard.main:app --app-dir src --reload
```

The OpenAPI docs are available at `http://127.0.0.1:8000/docs`.

### Environment Variables

| Variable                          | Description                    | Example                                        |
|-----------------------------------|--------------------------------|------------------------------------------------|
| `DATABASE_URL`                    | Async PostgreSQL connection    | `postgresql+asyncpg://postgres:root@localhost:5432/order_guard` |
| `ACCESS_TOKEN_EXPIRY_IN_MINUTES`  | Access token lifetime          | `30`                                           |
| `REFRESH_TOKEN_EXPIRY_IN_DAYS`    | Refresh token lifetime         | `7`                                            |
| `JWT_SECRET_KEY`                  | HS256 signing key              | `<random 64+ chars>`                           |
| `ALGORITHM`                       | JWT algorithm                  | `HS256`                                        |

`.env` is gitignored; never commit it.

## API Endpoints

### Auth (`/auth`)

| Method | Path                | Auth | Limit      | Description                  |
|--------|---------------------|------|------------|------------------------------|
| POST   | `/auth/register`    | –    | 10/min     | Create an account            |
| POST   | `/auth/login`       | –    | 10/min     | Get access + refresh tokens  |
| POST   | `/auth/refresh-token`| –   | 10/min     | Rotate refresh, new access   |

### Products (`/products`)

| Method  | Path                 | Auth | Limit    | Description                              |
|---------|----------------------|------|----------|------------------------------------------|
| GET     | `/products`          | –    | 60/min   | List/search catalog (paginated)          |
| GET     | `/products/{id}`     | –    | 60/min   | Product detail                           |
| POST    | `/products`          | Bearer | 10/min | Create product (owned by caller)         |
| PUT     | `/products/{id}`     | Bearer | 10/min | Update own product (`403` otherwise)     |
| DELETE  | `/products/{id}`     | Bearer | 10/min | Delete own product (`409` if already referenced by an order) |

### Cart (`/cart`)

| Method | Path                  | Auth | Limit  | Description                                    |
|--------|-----------------------|------|--------|--------------------------------------------------|
| GET    | `/cart`               | Bearer | 60/min | List your cart with line totals                  |
| POST   | `/cart/items`         | Bearer | 20/min | Add item (merges quantity, validates stock)      |
| PATCH  | `/cart/items/{item_id}` | Bearer | 20/min | Set quantity on your cart item                   |
| DELETE | `/cart/items/{item_id}` | Bearer | 20/min | Remove your cart item                            |

### Orders (`/orders`)

| Method | Path            | Auth | Limit | Description                                   |
|--------|-----------------|------|-------|------------------------------------------------|
| POST   | `/orders`       | Bearer | 10/min | Place order from cart (atomic, decrements stock, clears cart) |
| GET    | `/orders`       | Bearer | 60/min | List your orders (paginated, with items)       |
| GET    | `/orders/{id}`  | Bearer | 60/min | Your order detail (`404` for other users' orders) |

## Design Notes

- **Place order is atomic.** Stock checks, order + item snapshotting, stock decrement, and cart clearing all run in a single transaction — any failure rolls everything back.
- **Order items snapshot name and price.** Historical orders stay correct even if the product is later edited or deleted (deletion is blocked while referenced, `409`).
- **Retries are applied to write paths only** (`create/update/delete product`, cart mutations, `place_order`) via the `@db_retry` decorator: 3 attempts, exponential backoff, on transient SQLAlchemy `OperationalError`/`InterfaceError`. Reads are not retried.
- **Rate limits are per client IP** (SlowAPI's `get_remote_address`). Limits are tuned so auth and order placement stay strict while browsing endpoints remain comfortable.

## Roadmap

- [ ] AI microservice (recommendations / order summarisation) — separate deployment, communicating over HTTP
- [ ] Order status transitions (confirm → ship → deliver)
- [ ] Test suite + CI
