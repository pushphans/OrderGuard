import uuid
from decimal import Decimal
from orderguard.core.errors import CartEmptyError
from orderguard.core.errors import InsufficientStockError
from orderguard.core.enums import OrderStatus
from orderguard.orders.model.order_model import OrderModel, OrderItemModel
from orderguard.orders.schema.order_schema import OrderItemResponseSchema
from orderguard.orders.schema.order_schema import OrderResponseSchema
from orderguard.cart.service.cart_service import get_cart_items_for_user
from orderguard.core.retry import db_retry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@db_retry
async def place_order(
    db : AsyncSession,
    user_id : uuid.UUID
):
    try:
        cart_items = await get_cart_items_for_user(db=db, user_id=user_id)

        if not cart_items:
            raise CartEmptyError

        total_price : Decimal = Decimal("0")

        for item, product in cart_items:
            if item.quantity > product.stock_quantity:
                raise InsufficientStockError

            total_price += product.price * item.quantity

        order = OrderModel(
            user_id = user_id,
            status = OrderStatus.PENDING,
            total_price = total_price
        )

        db.add(order)
        await db.flush()

        for item, product in cart_items:
            order_item = OrderItemModel(
                order_id = order.id,
                product_id = product.id,
                name = product.name,
                price = product.price,
                quantity = item.quantity,
                line_total = product.price * item.quantity
            )

            db.add(order_item)

            product.stock_quantity -= item.quantity
            await db.delete(item)

        await db.commit()
        await db.refresh(order)

        return await get_order(db=db, user_id=user_id, order_id=order.id)

    except Exception:
        await db.rollback()
        raise



async def get_order(
    db : AsyncSession,
    user_id : uuid.UUID,
    order_id : uuid.UUID
):
    order_query = (
        select(OrderModel)
        .where(OrderModel.id == order_id, OrderModel.user_id == user_id)
    )

    order_result = await db.execute(order_query)
    order = order_result.scalar_one_or_none()

    if order is None:
        raise LookupError

    items_query = (
        select(OrderItemModel)
        .where(OrderItemModel.order_id == order.id)
    )

    items_result = await db.execute(items_query)
    order_items = items_result.scalars().all()

    return OrderResponseSchema(
        order_id=order.id,
        user_id=order.user_id,
        status=order.status,
        total_price=order.total_price,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[
            OrderItemResponseSchema(
                product_id=item.product_id,
                name=item.name,
                price=item.price,
                quantity=item.quantity,
                line_total=item.line_total
            )
            for item in order_items
        ]
    )



async def list_orders(
    db : AsyncSession,
    user_id : uuid.UUID,
    page_number : int = 1,
    page_size : int = 10
):
    query = (
        select(OrderModel)
        .where(OrderModel.user_id == user_id)
        .order_by(OrderModel.created_at.desc())
        .offset((page_number - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)

    orders = result.scalars().all()

    items_query = (
        select(OrderItemModel)
        .where(OrderItemModel.order_id.in_([order.id for order in orders]))
    )

    items_result = await db.execute(items_query)
    all_items = items_result.scalars().all()

    items_by_order: dict[uuid.UUID, list[OrderItemModel]] = {}

    for item in all_items:
        items_by_order.setdefault(item.order_id, []).append(item)

    return [
        OrderResponseSchema(
            order_id=order.id,
            user_id=order.user_id,
            status=order.status,
            total_price=order.total_price,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=[
                OrderItemResponseSchema(
                    product_id=item.product_id,
                    name=item.name,
                    price=item.price,
                    quantity=item.quantity,
                    line_total=item.line_total
                )
                for item in items_by_order.get(order.id, [])
            ]
        )
        for order in orders
    ]
