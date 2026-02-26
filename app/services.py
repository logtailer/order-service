from datetime import datetime
from sqlalchemy import func
from app import db
from app.models import Order, OrderItem, OrderStatusHistory, StatusEnum


def create_new_order(order_data):
    try:
        new_order = Order(
            user_id=order_data.get('user_id'),
            status=order_data.get('status').upper(),
            notes=order_data.get('notes'),
        )

        total_price = 0
        for item_data in order_data.get('items', []):
            price = item_data.get('price')
            quantity = item_data.get('quantity')
            total_price += price * quantity
            new_order.items.append(OrderItem(
                product_id=item_data.get('product_id'),
                quantity=quantity,
                price=price,
            ))

        new_order.total_price = total_price
        db.session.add(new_order)
        db.session.flush()
        db.session.add(OrderStatusHistory(
            order_id=new_order.id,
            from_status=None,
            to_status=new_order.status,
        ))
        db.session.commit()
        return new_order.id
    except Exception:
        db.session.rollback()
        raise


def _build_orders_query(created_after=None, created_before=None,
                        updated_after=None, updated_before=None,
                        status=None, user_id=None, min_price=None, max_price=None):
    query = Order.query
    if created_after:
        query = query.filter(Order.created_at >= created_after)
    if created_before:
        query = query.filter(Order.created_at <= created_before)
    if updated_after:
        query = query.filter(Order.updated_at >= updated_after)
    if updated_before:
        query = query.filter(Order.updated_at <= updated_before)
    if status:
        query = query.filter(Order.status == status.upper())
    if user_id:
        query = query.filter(Order.user_id == user_id)
    if min_price is not None:
        query = query.filter(Order.total_price >= min_price)
    if max_price is not None:
        query = query.filter(Order.total_price <= max_price)
    return query


def get_all_orders(page=1, per_page=20, created_after=None, created_before=None,
                   updated_after=None, updated_before=None,
                   sort_by='created_at', sort_order='desc', status=None, user_id=None,
                   min_price=None, max_price=None):
    query = _build_orders_query(
        created_after=created_after, created_before=created_before,
        updated_after=updated_after, updated_before=updated_before,
        status=status, user_id=user_id,
        min_price=min_price, max_price=max_price,
    )
    sort_column = getattr(Order, sort_by, Order.created_at)
    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'orders': [order.to_dict() for order in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'per_page': pagination.per_page,
    }


def get_order_by_id(order_id):
    order = db.session.get(Order, order_id)
    return order.to_dict() if order else None


def update_order_status(order_id, status_data, reason=None):
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return False

        terminal_statuses = {StatusEnum.DELIVERED, StatusEnum.CANCELLED}
        if order.status in terminal_statuses:
            raise ValueError(f"Order is already {order.status.value} and cannot be updated")

        prev_status = order.status
        order.status = status_data.get('status').upper()
        order.updated_at = datetime.utcnow()
        db.session.add(OrderStatusHistory(
            order_id=order.id,
            from_status=prev_status,
            to_status=order.status,
            reason=reason,
        ))
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        raise


def get_orders_by_user(user_id):
    orders = Order.query.filter_by(user_id=user_id).all()
    return [order.to_dict(include_items=False) for order in orders]


def cancel_order(order_id, reason=None):
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return False
        prev_status = order.status
        order.status = StatusEnum.CANCELLED
        order.updated_at = datetime.utcnow()
        db.session.add(OrderStatusHistory(
            order_id=order.id,
            from_status=prev_status,
            to_status=StatusEnum.CANCELLED,
            reason=reason,
        ))
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        raise


def get_orders_summary():
    results = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    summary = {s.value: 0 for s in StatusEnum}
    for status, count in results:
        summary[status.value] = count
    return summary


def bulk_update_status(order_ids, new_status):
    updated, skipped = [], []
    terminal_statuses = {StatusEnum.DELIVERED, StatusEnum.CANCELLED}
    now = datetime.utcnow()

    for order_id in order_ids:
        order = db.session.get(Order, order_id)
        if not order or order.status in terminal_statuses:
            skipped.append(order_id)
            continue
        order.status = new_status.upper()
        order.updated_at = now
        updated.append(order_id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {"updated": updated, "skipped": skipped}


def update_order_notes(order_id, notes):
    order = db.session.get(Order, order_id)
    if not order:
        return False
    order.notes = notes
    order.updated_at = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return True


def count_orders(status=None, user_id=None):
    query = Order.query
    if status:
        query = query.filter(Order.status == status.upper())
    if user_id:
        query = query.filter(Order.user_id == user_id)
    return query.count()


def get_order_history(order_id):
    rows = (
        OrderStatusHistory.query
        .filter_by(order_id=order_id)
        .order_by(OrderStatusHistory.changed_at.asc())
        .all()
    )
    return [r.to_dict() for r in rows]


def get_orders_by_status(status):
    orders = Order.query.filter_by(status=status.upper()).all()
    return [order.to_dict() for order in orders]


def update_order_item(order_id, item_id, quantity):
    order = db.session.get(Order, order_id)
    if not order:
        return None

    terminal_statuses = {StatusEnum.DELIVERED, StatusEnum.CANCELLED}
    if order.status in terminal_statuses:
        raise ValueError(f"Cannot modify items on a {order.status.value} order")

    item = OrderItem.query.filter_by(id=item_id, order_id=order_id).first()
    if not item:
        return None

    item.quantity = quantity
    order.total_price = sum(i.price * i.quantity for i in order.items)
    order.updated_at = datetime.utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return item.to_dict()


def get_order_items(order_id, product_id=None):
    query = OrderItem.query.filter_by(order_id=order_id)
    if product_id is not None:
        query = query.filter_by(product_id=product_id)
    return [item.to_dict() for item in query.all()]
