import uuid
from orderguard.core.errors import InsufficientStockError
from orderguard.core.errors import StockLimitExceededError
from orderguard.cart.model.cart_model import CartItemModel
from orderguard.products.model.product_model import ProductModel
from orderguard.cart.schema.cart_schema import AddCartItemRequestSchema
from orderguard.cart.schema.cart_schema import UpdateCartItemQuantitySchema
from orderguard.cart.schema.cart_schema import CartItemResponseSchema
from orderguard.core.retry import db_retry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@db_retry
async def add_to_cart(
    db : AsyncSession,
    user_id : uuid.UUID,
    data : AddCartItemRequestSchema
):
    try:
        product_query = (
            select(ProductModel)
            .where(ProductModel.id == data.product_id)
        )

        product_result = await db.execute(product_query)
        product = product_result.scalar_one_or_none()

        if product is None:
            raise LookupError

        item_query = (
            select(CartItemModel)
            .where(CartItemModel.user_id == user_id, CartItemModel.product_id == data.product_id)
        )

        item_result = await db.execute(item_query)
        cart_item = item_result.scalar_one_or_none()

        new_quantity = data.quantity if cart_item is None else cart_item.quantity + data.quantity

        if new_quantity > product.stock_quantity:
            raise StockLimitExceededError

        if cart_item is None:
            cart_item = CartItemModel(
                user_id = user_id,
                product_id = data.product_id,
                quantity = new_quantity
            )

            db.add(cart_item)

        else:
            cart_item.quantity = new_quantity

        await db.commit()
        await db.refresh(cart_item)

        return CartItemResponseSchema(
            item_id=cart_item.id,
            product_id=data.product_id,
            name=product.name,
            price=product.price,
            quantity=cart_item.quantity,
            line_total=product.price * cart_item.quantity,
            created_at=cart_item.created_at
        )

    except Exception:
        await db.rollback()
        raise



async def list_cart(
    db : AsyncSession,
    user_id : uuid.UUID
):
    query = (
        select(CartItemModel, ProductModel)
        .join(ProductModel, ProductModel.id == CartItemModel.product_id)
        .where(CartItemModel.user_id == user_id)
        .order_by(CartItemModel.created_at.desc())
    )

    result = await db.execute(query)

    rows = result.all()

    return [
        CartItemResponseSchema(
            item_id=item.id,
            product_id=item.product_id,
            name=product.name,
            price=product.price,
            quantity=item.quantity,
            line_total=product.price * item.quantity,
            created_at=item.created_at
        )
        for item, product in rows
    ]



@db_retry
async def update_cart_item_quantity(
    db : AsyncSession,
    user_id : uuid.UUID,
    item_id : uuid.UUID,
    data : UpdateCartItemQuantitySchema
):
    try:
        item_query = (
            select(CartItemModel)
            .where(CartItemModel.id == item_id, CartItemModel.user_id == user_id)
        )

        item_result = await db.execute(item_query)
        cart_item = item_result.scalar_one_or_none()

        if cart_item is None:
            raise LookupError

        product_query = (
            select(ProductModel)
            .where(ProductModel.id == cart_item.product_id)
        )

        product_result = await db.execute(product_query)
        product = product_result.scalar_one_or_none()

        if product is None:
            raise LookupError

        if data.quantity > product.stock_quantity:
            raise StockLimitExceededError

        cart_item.quantity = data.quantity

        await db.commit()
        await db.refresh(cart_item)

        return CartItemResponseSchema(
            item_id=cart_item.id,
            product_id=cart_item.product_id,
            name=product.name,
            price=product.price,
            quantity=cart_item.quantity,
            line_total=product.price * cart_item.quantity,
            created_at=cart_item.created_at
        )

    except Exception:
        await db.rollback()
        raise



@db_retry
async def remove_cart_item(
    db : AsyncSession,
    user_id : uuid.UUID,
    item_id : uuid.UUID
):
    try:
        item_query = (
            select(CartItemModel)
            .where(CartItemModel.id == item_id, CartItemModel.user_id == user_id)
        )

        item_result = await db.execute(item_query)
        cart_item = item_result.scalar_one_or_none()

        if cart_item is None:
            raise LookupError

        await db.delete(cart_item)
        await db.commit()

        return {"removed": str(item_id)}

    except Exception:
        await db.rollback()
        raise



async def get_cart_items_for_user(
    db : AsyncSession,
    user_id : uuid.UUID
):
    query = (
        select(CartItemModel, ProductModel)
        .join(ProductModel, ProductModel.id == CartItemModel.product_id)
        .where(CartItemModel.user_id == user_id)
    )

    result = await db.execute(query)

    return result.all()
