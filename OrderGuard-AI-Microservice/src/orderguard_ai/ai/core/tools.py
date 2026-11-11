import json
import uuid
from typing import Annotated

from langchain_core.tools import BaseTool, tool
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from orderguard_ai.cart.schema.cart_schema import AddCartItemRequestSchema
from orderguard_ai.cart.schema.cart_schema import UpdateCartItemQuantitySchema
from orderguard_ai.cart.service.cart_service import add_to_cart
from orderguard_ai.cart.service.cart_service import list_cart
from orderguard_ai.cart.service.cart_service import update_cart_item_quantity
from orderguard_ai.cart.service.cart_service import remove_cart_item
from orderguard_ai.orders.service.order_service import place_order as place_order_service
from orderguard_ai.orders.service.order_service import list_orders
from orderguard_ai.orders.service.order_service import get_order
from orderguard_ai.core.product_client import ProductClient
from orderguard_ai.core.errors import CatalogUnavailableError
from orderguard_ai.core.errors import StockLimitExceededError
from orderguard_ai.core.errors import CartEmptyError
from orderguard_ai.core.errors import InsufficientStockError


def search_product_tools(client: ProductClient) -> list[BaseTool]:
    @tool
    async def search_products(
        name: Annotated[str, Field(description="Product name or keyword to search the catalog")]
    ) -> str:
        """Search the shop catalog. Returns a JSON list of matching products (id, name, price, stock)."""
        try:
            products = await client.search_products(search=name)
            return json.dumps([product.model_dump(mode="json") for product in products], indent=2)
        except CatalogUnavailableError as error:
            return json.dumps({"error": f"Catalog unavailable: {error}"})

    return [search_products]


def cart_tools(
    db: AsyncSession,
    user_id: uuid.UUID,
    client: ProductClient,
) -> list[BaseTool]:
    @tool
    async def add_item_to_cart(
        product_id: Annotated[uuid.UUID, Field(description="ID of the product to add (from search_products)")],
        quantity: Annotated[int, Field(description="Quantity to add", ge=1, le=100)] = 1,
    ) -> str:
        """Add a product to the user's shopping cart. Quantities for the same product are merged. Returns the updated cart item as JSON, or an error."""
        try:
            result = await add_to_cart(
                db,
                user_id,
                AddCartItemRequestSchema(product_id=product_id, quantity=quantity),
                client
            )
            return json.dumps(result.model_dump(mode="json"), indent=2)
        except StockLimitExceededError:
            return json.dumps({"error": "Quantity exceeds available stock"})
        except LookupError:
            return json.dumps({"error": "Product not found"})
        except CatalogUnavailableError as error:
            return json.dumps({"error": f"Catalog unavailable: {error}"})

    @tool
    async def list_user_cart() -> str:
        """List the user's current shopping cart with live product details. Returns a JSON list of cart items."""
        items = await list_cart(db, user_id, client)
        return json.dumps([item.model_dump(mode="json") for item in items], indent=2)

    @tool
    async def update_cart_item_quantity(
        item_id: Annotated[uuid.UUID, Field(description="Cart item ID (from list_user_cart)")],
        quantity: Annotated[int, Field(description="New quantity for the item", ge=1, le=100)],
    ) -> str:
        """Set the quantity of one of the user's cart items. Returns the updated item as JSON, or an error."""
        try:
            result = await update_cart_item_quantity(
                db,
                user_id,
                item_id,
                UpdateCartItemQuantitySchema(quantity=quantity),
                client
            )
            return json.dumps(result.model_dump(mode="json"), indent=2)
        except StockLimitExceededError:
            return json.dumps({"error": "Quantity exceeds available stock"})
        except LookupError:
            return json.dumps({"error": "Cart item or product not found"})
        except CatalogUnavailableError as error:
            return json.dumps({"error": f"Catalog unavailable: {error}"})

    @tool
    async def remove_cart_item(
        item_id: Annotated[uuid.UUID, Field(description="Cart item ID (from list_user_cart)")],
    ) -> str:
        """Remove one item from the user's shopping cart. Returns a JSON confirmation, or an error."""
        try:
            result = await remove_cart_item(db, user_id, item_id)
            return json.dumps(result)
        except LookupError:
            return json.dumps({"error": "Cart item not found"})

    return [*search_product_tools(client), add_item_to_cart, list_user_cart, update_cart_item_quantity, remove_cart_item]


def order_tools(
    db: AsyncSession,
    user_id: uuid.UUID,
    client: ProductClient,
) -> list[BaseTool]:
    @tool
    async def place_order() -> str:
        """Place an order for everything currently in the user's cart. Stock is validated, the cart is cleared, and stock is decremented. Returns the created order as JSON, or an error."""
        try:
            order = await place_order_service(db, user_id, client)
            return json.dumps(order.model_dump(mode="json"), indent=2)
        except CartEmptyError:
            return json.dumps({"error": "Cart is empty. Add items to the cart before placing an order."})
        except LookupError:
            return json.dumps({"error": "A product in the cart no longer exists. Remove it first."})
        except InsufficientStockError:
            return json.dumps({"error": "Insufficient stock for one or more items."})
        except CatalogUnavailableError as error:
            return json.dumps({"error": f"Catalog unavailable: {error}"})

    @tool
    async def list_user_orders() -> str:
        """List the user's recent orders with their items. Returns a JSON list of orders."""
        orders = await list_orders(db, user_id)
        return json.dumps([order.model_dump(mode="json") for order in orders], indent=2)

    @tool
    async def get_order_details(
        order_id: Annotated[uuid.UUID, Field(description="Order ID (from list_user_orders)")],
    ) -> str:
        """Get the full details of one of the user's orders. Returns the order as JSON, or an error."""
        try:
            order = await get_order(db, user_id, order_id)
            return json.dumps(order.model_dump(mode="json"), indent=2)
        except LookupError:
            return json.dumps({"error": "Order not found"})

    @tool
    async def list_user_cart() -> str:
        """List the user's current shopping cart, so you can confirm what an order will contain. Returns a JSON list of cart items."""
        items = await list_cart(db, user_id, client)
        return json.dumps([item.model_dump(mode="json") for item in items], indent=2)

    return [place_order, list_user_orders, get_order_details, list_user_cart]
