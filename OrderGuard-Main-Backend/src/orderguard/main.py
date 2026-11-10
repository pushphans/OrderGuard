from orderguard.auth.router.auth_router import auth_router
from orderguard.products.router.product_router import product_router
from orderguard.cart.router.cart_router import cart_router
from orderguard.orders.router.order_router import order_router
from fastapi import FastAPI
from fastapi import Request
from fastapi import status
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from orderguard.auth.utils.current_user_utils import InvalidTokenError
from orderguard.auth.utils.current_user_utils import InvalidCredentialError
from jwt.exceptions import PyJWTError
from orderguard.core.limiter import limiter


app = FastAPI(title="OrderGuard")


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



@app.exception_handler(InvalidTokenError)
async def handle_invalid_token(request: Request, exc: InvalidTokenError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Not authenticated"}
    )



@app.exception_handler(InvalidCredentialError)
async def handle_invalid_credential(request: Request, exc: InvalidCredentialError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid credentials"}
    )



@app.exception_handler(PyJWTError)
async def handle_jwt_error(request: Request, exc: PyJWTError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid or expired token"}
    )


app.include_router(auth_router)
app.include_router(product_router)
app.include_router(cart_router)
app.include_router(order_router)


@app.get("/")
@limiter.limit("60/minute")
async def health_check(request: Request):
    return {
        "status": "ok"
    }
