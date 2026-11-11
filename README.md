# OrderGuard

A portfolio-grade e-commerce platform split across two services:

- **`OrderGuard-Main-Backend`** – core commerce foundation: user auth (JWT + Argon2) and the product catalog, with an internal service-to-service API for stock writes.
- **`OrderGuard-AI-Microservice`** – commerce operations: cart and orders, plus an **AI supervisor workflow** so users can manage their cart and orders in plain language.

```
                ┌──────────────────────────────────────────────┐
   user (JWT)   │            OrderGuard Main Backend           │
 ──────────────▶│  /auth (register·login·refresh)             │
                │  /products (catalog + stock)                │
                │  /internal (stock writes, service-secret)   │
                └───────────────▲──────────────────────────────┘
                                 │  httpx (reads + stock writes)
                                 │  X-Service-Token: shared secret
                ┌───────────────┴──────────────────────────────┐
                │            OrderGuard AI Microservice         │
                │  /cart  /orders      (REST)                  │
                │  /ai/chat ─▶ supervisor ─▶ cart agent        │
                │                     └──▶ orders agent        │
                └────────────────────────────────────────────────┘
        (own PostgreSQL: cart_items, orders, order_items)
```

| Concern                              | Service            |
|--------------------------------------|--------------------|
| Users, JWT auth, refresh tokens      | Main Backend       |
| Product catalog + stock of record    | Main Backend       |
| Cart, orders, order history          | AI Microservice    |
| AI-driven cart/order tools           | AI Microservice    |

## Features

**Main Backend**

- Register / login / rotating refresh tokens; Argon2 password hashing; short-lived HS256 access tokens
- Product catalog with per-owner CRUD and ownership checks (`403` for outsiders, `404` to hide existence)
- Per-endpoint rate limiting (SlowAPI) and transient-DB retry on write paths (Tenacity)
- Internal, service-to-service stock-decrement endpoint authenticated by a shared service secret

**AI Microservice**

- Cart + orders REST API with live stock validation against the main backend
- Atomic order placement: stock check, snapshot, cart clear locally; stock decrement on the main backend via one atomic batch call
- **Supervisor multi-agent workflow** (LangGraph + LangChain-Groq): a routing supervisor drives a *cart agent* and an *orders agent*; both agents use the cart/order services as tools
- Order items snapshot name + price, so historical orders survive product edits/deletes
- JWT verified against the main backend's shared secret — users sign in once and use both services

## Repository layout

```
.
├── OrderGuard-Main-Backend/     # FastAPI: auth + products + internal S2S API
└── OrderGuard-AI-Microservice/  # FastAPI: cart + orders + AI supervisor workflow
```

Each service is self-contained (own `pyproject.toml`, `uv.lock`, migrations, `.env` template, README).

## Prerequisites

- Python 3.14+
- PostgreSQL on `localhost:5432`
- [uv](https://docs.astral.sh/uv/)
- A [Groq](https://console.groq.com/) API key (for the AI service's LLM calls)

## Getting started

### 1. Main backend

```bash
cd OrderGuard-Main-Backend
uv sync
cp .env.example .env          # set JWT_SECRET_KEY + SERVICE_SECRET
createdb order_guard         # or: psql -c "CREATE DATABASE order_guard;"
uv run alembic upgrade head
uv run uvicorn orderguard.main:app --app-dir src --port 8000 --reload
```

### 2. AI microservice

```bash
cd OrderGuard-AI-Microservice
uv sync
cp .env.example .env         # mirror the main backend's JWT_SECRET_KEY + SERVICE_SECRET, set GROQ_API_KEY
createdb order_guard_ai
uv run alembic upgrade head
uv run uvicorn orderguard_ai.main:app --app-dir src --port 8001 --reload
```

OpenAPI docs: `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8001/docs`.

## Environment variables

| Variable                     | Main Backend | AI Service | Description                              |
|------------------------------|:-----------:|:---------:|------------------------------------------|
| `DATABASE_URL`               | ✔ | ✔ | Each service's own async Postgres URL    |
| `JWT_SECRET_KEY` / `ALGORITHM` | ✔ | ✔ | **Shared** – the AI service verifies the main backend's access tokens |
| `ACCESS_TOKEN_EXPIRY_IN_MINUTES`, `REFRESH_TOKEN_EXPIRY_IN_DAYS` | ✔ | – | Token lifetimes                          |
| `SERVICE_SECRET`             | ✔ | ✔ | **Shared** – sent as `X-Service-Token` on internal S2S calls |
| `MAIN_BACKEND_URL`           | – | ✔ | Base URL of the main backend             |
| `GROQ_API_KEY`               | – | ✔ | Groq key for the supervisor / agents     |

`.env` files are gitignored — never commit real secrets.

## Security model

- **Users** authenticate against the main backend; the AI service only *verifies* those JWTs (shared HS256 secret) and acts on the token's `user_id`.
- **Ownership** is enforced on every read/write of cart/order rows (`WHERE user_id = caller`), so other users' data is unreachable (`404` hides existence).
- **Service-to-service** writes (stock decrement) go through `/internal/...` guarded by the shared `SERVICE_SECRET` in the `X-Service-Token` header — the catalog's public read endpoints stay open, internal writes are not.
- **Rate limits** (per-IP) keep auth and order-placement strict while browsing stays comfortable.
- **Order placement is atomic on the main backend side** (one conditional batch stock update) and the AI service commits its local order only after that write succeeds — a failed decrement rolls the whole order back.

## Roadmap

- [ ] Order status transitions (confirm → ship → deliver) + admin surface
- [ ] Multi-turn AI conversation memory (checkpointer + thread per user)
- [ ] More agents under the supervisor (recommendations, support, catalog curation)
- [ ] Test suites + CI for both services

## License

MIT — see [OrderGuard-Main-Backend/LICENSE](OrderGuard-Main-Backend/LICENSE).
