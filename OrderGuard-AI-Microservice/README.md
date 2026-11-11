# OrderGuard AI (microservice)

The commerce-operations half of OrderGuard. It owns **cart** and **orders**, and
exposes them both as a regular REST API **and** as AI-driven tools through a
supervisor multi-agent workflow, so users can manage their carts and orders in
plain language.

It is intentionally an **internally monolithic** FastAPI service: one deployable,
clean layering (`model → schema → service → router`), talking to a separate
**main backend** over HTTP for product data.

## AI supervisor workflow

`/ai/chat` runs a LangGraph **supervisor** workflow:

```
            ┌────────────┐
   user ───▶ │ supervisor │ ── routes with a structured LLM decision
            └────┬───────┘
        ┌────────┴─────────┐
        ▼                  ▼
  ┌───────────┐      ┌─────────────┐
  │ cart agent │      │ orders agent │   ReAct tool-calling subagents
  └───────────┘      └─────────────┘   (langgraph prebuilt react agents)
        │                  │
        └────────┬─────────┘
                 ▼
          back to supervisor (loop) or FINISH
```

- **Supervisor** – an LLM that only routes: `cart` / `orders` / `FINISH`. It
  never answers the user itself; multi-part requests can flow through both
  agents in one run.
- **Cart agent** – tools: `search_products`, `add_item_to_cart`,
  `list_user_cart`, `update_cart_item_quantity`, `remove_cart_item`.
- **Orders agent** – tools: `place_order`, `list_user_orders`,
  `get_order_details`, `list_user_cart`.

The tools wrap the same service layer the REST endpoints use, so AI-driven
actions go through identical ownership checks, stock validation and the
cross-service stock decrement. All tools operate on **the caller's** cart /
orders only (the user id comes from the verified JWT).

The LLM is a Groq `llama-3.3-70b-versatile` chat model (LangChain-Groq); the
agent + supervisor structure mirrors the `CorpAssist` reference project.

## Split

| Concern | Lives in |
|---------|----------|
| Users, JWT auth, products (catalog + stock) | `OrderGuard-Main-Backend` |
| Cart, orders, (future) AI tools | this service |

This service keeps its own database for cart + orders. Product name / price /
stock are fetched from the main backend on demand; stock is decremented through
an internal, service-to-service endpoint.

## How it talks to the main backend

- **User verification** – this service shares the main backend's `JWT_SECRET_KEY`.
  Every protected route decodes the caller's access token, extracts the user id
  (`sub`), and uses it for ownership checks on cart / order rows. Expired or
  invalid tokens → `401`.
- **Product reads** – `GET /products/{id}` on the main backend.
- **Stock writes** – `POST /internal/products/decrement-stock` on the main
  backend, authenticated by a shared `SERVICE_SECRET` sent in the
  `X-Service-Token` header. Both services hold this secret.

## Tech Stack

| Layer      | Choice                                   |
|------------|------------------------------------------|
| Framework  | FastAPI (async)                          |
| Database   | PostgreSQL via SQLAlchemy 2 (asyncpg)    |
| Migrations | Alembic                                  |
| Auth       | PyJWT (verify only; issued by main svc)  |
| AI         | LangGraph (supervisor) + LangChain-Groq  |
| S2S        | httpx (product reads + stock writes)     |
| Resilience | SlowAPI (rate limits) + Tenacity (retry) |
| Tooling    | uv (env / deps / locking)                |

## Project Structure

```
.
├── alembic.ini
├── migrations/
└── src/
    └── orderguard_ai/
        ├── main.py             # app factory, lifespan (product client), routers
        ├── core/
        │   ├── config.py       # settings (.env)
        │   ├── db.py           # async engine, session factory, Base
        │   ├── enums.py        # OrderStatus
        │   ├── errors.py       # domain exceptions
        │   ├── limiter.py      # SlowAPI limiter
        │   ├── retry.py        # Tenacity db_retry
        │   └── product_client.py  # httpx client to the main backend
        ├── auth/               # JWT verify + get_user (user id from token)
        ├── cart/               # Cart item model / schema / service / router
        ├── orders/            # Order + order item models, service, router
        └── ai/
            ├── core/
            │   ├── llm.py      # get_llm (Groq chat model)
            │   ├── state.py    # AgentState (messages + context)
            │   └── tools.py    # cart_tools + order_tools (service wrappers)
            ├── workflow/
            │   ├── prompts.py  # supervisor + agent system prompts
            │   └── graph.py    # build_supervisor_workflow (LangGraph)
            ├── schema/ai_schema.py
            └── router/ai_router.py   # POST /ai/chat
```

## Getting Started

### Prerequisites

- Python 3.14+
- PostgreSQL running on `localhost:5432`
- The **main backend** running on `MAIN_BACKEND_URL`
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
# 1. install dependencies
uv sync

# 2. configure environment (mirror the main backend's JWT_SECRET_KEY)
cp .env.example .env

# 3. create this service's database
createdb order_guard_ai      # or: psql -c "CREATE DATABASE order_guard_ai;"

# 4. apply migrations
uv run alembic upgrade head

# 5. run the service
uv run uvicorn orderguard_ai.main:app --app-dir src --reload
```

The OpenAPI docs are available at `http://127.0.0.1:8001/docs`.

### Environment Variables

| Variable           | Description                                   |
|--------------------|-----------------------------------------------|
| `DATABASE_URL`     | Async PostgreSQL URL (this service's own DB)  |
| `JWT_SECRET_KEY`   | **Same** as the main backend (verify tokens)  |
| `ALGORITHM`        | JWT algorithm (`HS256`)                       |
| `MAIN_BACKEND_URL` | Base URL of the main backend                  |
| `SERVICE_SECRET`   | Shared secret for internal S2S calls          |
| `GROQ_API_KEY`     | Groq key for the AI supervisor / agents      |

## API Endpoints

### Cart (`/cart`)

| Method | Path                     | Auth   | Limit  | Description                              |
|--------|--------------------------|--------|--------|------------------------------------------|
| GET    | `/cart`                  | Bearer | 60/min | List your cart (product details live)    |
| POST   | `/cart/items`            | Bearer | 20/min | Add item (stock validated via main svc)  |
| PATCH  | `/cart/items/{item_id}`  | Bearer | 20/min | Set quantity on your cart item           |
| DELETE | `/cart/items/{item_id}`  | Bearer | 20/min | Remove your cart item                    |

### Orders (`/orders`)

| Method | Path            | Auth   | Limit  | Description                                   |
|--------|-----------------|--------|--------|-----------------------------------------------|
| POST   | `/orders`       | Bearer | 10/min | Place order (atomic, decrements stock S2S)    |
| GET    | `/orders`       | Bearer | 60/min | List your orders (paginated, with items)      |
| GET    | `/orders/{id}`  | Bearer | 60/min | Your order detail (`404` for others' orders)  |

### AI (`/ai`)

| Method | Path      | Auth   | Limit  | Description                                          |
|--------|-----------|--------|--------|------------------------------------------------------|
| POST   | `/ai/chat` | Bearer | 10/min | Talk to the supervisor; it drives cart + order tools |

`POST /ai/chat` takes `{"message": "..."}` and returns the assistant's answer
plus the routing `steps` taken by the supervisor. It needs `GROQ_API_KEY` to
be set (else `503`).

## Design Notes

- **Order items snapshot name + price** from the main backend, so historical
  orders stay correct even if a product is later edited or deleted.
- **Cross-service stock decrement is atomic on the main backend side** (a single
  conditional batch update) and runs *before* the local order commit, so a
  failed decrement rolls the whole order back.
- **`place_order` is deliberately not retried** (`@db_retry` is skipped there):
  it performs a non-idempotent HTTP stock write, and retrying could double-decrement.

## Roadmap

- [ ] AI recommendation / order summarisation features
- [ ] Multi-turn conversation memory (checkpointer + thread id per user)
- [ ] More agents (e.g. a `support` / `catalog` agent) under the same supervisor
