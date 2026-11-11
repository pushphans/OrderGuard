import asyncio
import uuid
from decimal import Decimal

import httpx
from pydantic import BaseModel
from fastapi import Request

from orderguard_ai.core.config import settings
from orderguard_ai.core.errors import CatalogUnavailableError
from orderguard_ai.core.errors import InsufficientStockError


class ProductInfo(BaseModel):
    product_id : uuid.UUID
    user_id : uuid.UUID
    name : str
    description : str | None
    price : Decimal
    stock_quantity : int


class _DecrementItem(BaseModel):
    product_id : uuid.UUID
    quantity : int


class _DecrementRequest(BaseModel):
    items : list[_DecrementItem]


class ProductClient:
    """HTTP client to the OrderGuard main backend (product reads + stock writes).

    Every call carries the shared ``X-Service-Token`` header so internal
    (service-to-service) writes are authenticated.
    """

    def __init__(
        self,
        base_url : str,
        service_secret : str,
        timeout : float = 10.0
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Service-Token": service_secret},
            timeout=timeout
        )

    async def get_product(
        self,
        product_id : uuid.UUID
    ) -> ProductInfo | None:
        try:
            response = await self._client.get(f"/products/{product_id}")
        except httpx.HTTPError as error:
            raise CatalogUnavailableError(str(error)) from error

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise CatalogUnavailableError(f"Unexpected status {response.status_code}")

        return ProductInfo(**response.json())

    async def get_products(
        self,
        product_ids : list[uuid.UUID]
    ) -> dict[uuid.UUID, ProductInfo]:
        unique_ids = list(dict.fromkeys(product_ids))

        async def _fetch(product_id : uuid.UUID) -> tuple[uuid.UUID, ProductInfo | None]:
            return product_id, await self.get_product(product_id)

        fetched = await asyncio.gather(*(_fetch(product_id) for product_id in unique_ids))

        return {
            product_id: product
            for product_id, product in fetched
            if product is not None
        }

    async def search_products(
        self,
        search : str | None = None,
        page_number : int = 1,
        page_size : int = 20
    ) -> list[ProductInfo]:
        params : dict[str, object] = {"page_number": page_number, "page_size": page_size}

        if search:
            params["search"] = search

        try:
            response = await self._client.get("/products", params=params)
        except httpx.HTTPError as error:
            raise CatalogUnavailableError(str(error)) from error

        if response.status_code != 200:
            raise CatalogUnavailableError(f"Unexpected status {response.status_code}")

        return [ProductInfo(**entry) for entry in response.json()]

    async def decrement_stock_batch(
        self,
        items : list[tuple[uuid.UUID, int]]
    ) -> dict[uuid.UUID, int]:
        payload = _DecrementRequest(
            items=[_DecrementItem(product_id=product_id, quantity=quantity) for product_id, quantity in items]
        )

        try:
            response = await self._client.post(
                "/internal/products/decrement-stock",
                json=payload.model_dump(mode="json")
            )
        except httpx.HTTPError as error:
            raise CatalogUnavailableError(str(error)) from error

        if response.status_code == 409:
            raise InsufficientStockError("Insufficient stock for one or more items")

        if response.status_code in (403, 404, 422) or response.status_code >= 500:
            raise CatalogUnavailableError(f"Stock decrement failed with status {response.status_code}")

        if response.status_code != 200:
            raise CatalogUnavailableError(f"Unexpected status {response.status_code}")

        data = response.json()

        return {
            entry["product_id"]: entry["new_stock"]
            for entry in data["results"]
        }

    async def aclose(self) -> None:
        await self._client.aclose()


async def get_product_client(request : Request) -> ProductClient:
    return request.app.state.product_client


def build_product_client() -> ProductClient:
    return ProductClient(
        base_url=settings.MAIN_BACKEND_URL,
        service_secret=settings.SERVICE_SECRET
    )
