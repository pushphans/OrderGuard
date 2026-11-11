from contextlib import asynccontextmanager

from orderguard_ai.cart.router.cart_router import cart_router
from orderguard_ai.orders.router.order_router import order_router
from orderguard_ai.ai.router.ai_router import ai_router
from orderguard_ai.core.limiter import limiter
from orderguard_ai.core.product_client import build_product_client
from orderguard_ai.core.errors import InvalidTokenError
from orderguard_ai.core.errors import CatalogUnavailableError
from fastapi import FastAPI
from fastapi import Request
from fastapi import status
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded



@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.product_client = build_product_client()
    yield
    await app.state.product_client.aclose()



app = FastAPI(title="OrderGuard AI", lifespan=lifespan)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



@app.exception_handler(InvalidTokenError)
async def handle_invalid_token(request: Request, exc: InvalidTokenError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Not authenticated"}
    )



@app.exception_handler(CatalogUnavailableError)
async def handle_catalog_unavailable(request: Request, exc: CatalogUnavailableError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Product catalog is unavailable"}
    )



app.include_router(cart_router)
app.include_router(order_router)
app.include_router(ai_router)



@app.get("/")
@limiter.limit("60/minute")
async def health_check(request: Request):
    return {
        "status": "ok"
    }
