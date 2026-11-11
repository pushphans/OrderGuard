import uuid
from orderguard.core.errors import IncompleteCredentialsError
from orderguard.core.errors import NotOwnerError
from orderguard.core.errors import InsufficientStockError
from orderguard.products.model.product_model import ProductModel
from orderguard.products.schema.product_schema import CreateProductRequestSchema
from orderguard.products.schema.product_schema import UpdateProductRequestSchema
from orderguard.products.schema.product_schema import ProductResponseSchema
from orderguard.core.retry import db_retry
from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Query


@db_retry
async def create_product(
    db : AsyncSession,
    user_id : uuid.UUID,
    data : CreateProductRequestSchema
):
    try:
        product_object = ProductModel(
            user_id = user_id,
            name = data.name,
            description = data.description,
            price = data.price,
            stock_quantity = data.stock_quantity
        )

        db.add(product_object)
        await db.commit()
        await db.refresh(product_object)

        return ProductResponseSchema(
            product_id=product_object.id,
            user_id=user_id,
            name=product_object.name,
            description=product_object.description,
            price=product_object.price,
            stock_quantity=product_object.stock_quantity,
            created_at=product_object.created_at,
            updated_at=product_object.updated_at
        )

    except Exception:
        await db.rollback()
        raise



@db_retry
async def get_product(
    db : AsyncSession,
    product_id : uuid.UUID
):
    query = (
        select(ProductModel)
        .where(ProductModel.id == product_id)
    )

    result = await db.execute(query)

    product_object = result.scalar_one_or_none()

    if product_object is None:
        raise LookupError

    return ProductResponseSchema(
        product_id=product_object.id,
        user_id=product_object.user_id,
        name=product_object.name,
        description=product_object.description,
        price=product_object.price,
        stock_quantity=product_object.stock_quantity,
        created_at=product_object.created_at,
        updated_at=product_object.updated_at
    )



@db_retry
async def list_products(
    db : AsyncSession,
    page_number : int = Query(default=1, ge=1),
    page_size : int = Query(default=10, le=100),
    search : str | None = Query(default=None, max_length=80)
):
    query = select(ProductModel)

    if search:
        query = (
            query
            .where(func.lower(ProductModel.name).ilike(f"%{search.lower()}%"))
        )

    offset = (page_number - 1) * page_size

    query = (
        query
        .order_by(func.coalesce(ProductModel.updated_at, ProductModel.created_at).desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)

    return result.scalars().all()



@db_retry
async def update_product(
    db : AsyncSession,
    user_id : uuid.UUID,
    product_id : uuid.UUID,
    data : UpdateProductRequestSchema
):
    try:
        query = (
            select(ProductModel)
            .where(ProductModel.id == product_id)
        )

        result = await db.execute(query)

        product_object = result.scalar_one_or_none()

        if product_object is None:
            raise LookupError

        if product_object.user_id != user_id:
            raise NotOwnerError

        product_object.name = data.name
        product_object.description = data.description
        product_object.price = data.price
        product_object.stock_quantity = data.stock_quantity

        await db.commit()
        await db.refresh(product_object)

        return ProductResponseSchema(
            product_id=product_object.id,
            user_id=product_object.user_id,
            name=product_object.name,
            description=product_object.description,
            price=product_object.price,
            stock_quantity=product_object.stock_quantity,
            created_at=product_object.created_at,
            updated_at=product_object.updated_at
        )

    except Exception:
        await db.rollback()
        raise



@db_retry
async def delete_product(
    db : AsyncSession,
    user_id : uuid.UUID,
    product_id : uuid.UUID
):
    try:
        query = (
            select(ProductModel)
            .where(ProductModel.id == product_id)
        )

        result = await db.execute(query)

        product_object = result.scalar_one_or_none()

        if product_object is None:
            raise LookupError

        if product_object.user_id != user_id:
            raise NotOwnerError

        await db.delete(product_object)
        await db.commit()

        return {"deleted": str(product_id)}

    except Exception:
        await db.rollback()
        raise


@db_retry
async def decrement_stock_batch(
    db : AsyncSession,
    items : list[tuple[uuid.UUID, int]]
):
    """Atomically decrement stock for a batch of products.

    All-or-nothing: if any product is missing or has insufficient stock, the
    entire batch rolls back. Intended for the internal service-to-service
    stock write used by the AI microservice when placing orders.
    """
    try:
        results : list[dict] = []

        for product_id, quantity in items:
            query = (
                select(ProductModel)
                .where(ProductModel.id == product_id)
                .with_for_update()
            )

            result = await db.execute(query)
            product_object = result.scalar_one_or_none()

            if product_object is None:
                raise LookupError

            if product_object.stock_quantity < quantity:
                raise InsufficientStockError

            product_object.stock_quantity -= quantity
            results.append({"product_id": str(product_id), "new_stock": product_object.stock_quantity})

        await db.commit()

        return results

    except Exception:
        await db.rollback()
        raise
