"""
The 'OrderService' module manages operations related to orders within the application.
It includes functionalities for creating, retrieving, updating, and canceling orders,
as well as calculating order totals and fetching orders based on specific criteria.
"""
from datetime import datetime
from app import db
from app.models import Order, OrderItem, OrderStatusHistory, StatusEnum

class OrderService:
    """
    A class handling various operations related to orders.
    """

    def create_new_order(self, order_data):
        """
        Creates a new order.

        Args:
        - order_data (dict): Data for the new order.

        Returns:
        - int: The ID of the created order.

        Raises:
        - Exception: If an error occurs during order creation.
        """
        try:
            user_id = order_data.get('user_id')
            status = order_data.get('status')

            items_data = order_data.get('items', [])

            # Create the Order object
            new_order = Order(
                user_id=user_id,
                status=status.upper(),
            )

            total_price = 0

            # Add OrderItems to the new order and calculate total price
            for item_data in items_data:
                price = item_data.get('price')
                quantity = item_data.get('quantity')
                total_price += price * quantity

                new_order.items.append(OrderItem(
                    product_id=item_data.get('product_id'),
                    quantity=quantity,
                    price=price
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
        except Exception as exception:
            db.session.rollback()
            raise exception

    def _build_orders_query(self, created_after=None, created_before=None,
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

    def get_all_orders(self, page=1, per_page=20, created_after=None, created_before=None,
                       updated_after=None, updated_before=None,
                       sort_by='created_at', sort_order='desc', status=None, user_id=None,
                       min_price=None, max_price=None):
        """
        Fetches a paginated list of orders from the database.

        Returns:
        dict: A dict with 'orders' list plus pagination metadata.
        """
        query = self._build_orders_query(
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

    def get_order_by_id(self, order_id):
        """
        Retrieves an order by its ID.

        Args:
        - order_id (int): ID of the order to retrieve.

        Returns:
        - dict or None: Serialized order data if found, else None.

        Raises:
        - Exception: If an error occurs during order retrieval.
        """
        try:
            order = db.session.get(Order, order_id)
            return order.to_dict() if order else None
        except Exception as exception:
            raise exception

    def update_order_status(self, order_id, status_data, reason=None):
        """
        Update the status of an order by order ID.

        Args:
        - order_id (int): ID of the order to update.
        - status_data (dict): Dictionary containing the new status data.

        Returns:
        - bool: True if the order status is updated successfully, else False.
        """
        try:
            order = db.session.get(Order, order_id)

            if not order:
                return False

            terminal_statuses = {StatusEnum.DELIVERED, StatusEnum.CANCELLED}
            if order.status in terminal_statuses:
                raise ValueError(f"Order is already {order.status.value} and cannot be updated")

            new_status = status_data.get('status')
            prev_status = order.status
            order.status = new_status.upper()
            order.updated_at = datetime.utcnow()
            db.session.add(OrderStatusHistory(
                order_id=order.id,
                from_status=prev_status,
                to_status=order.status,
                reason=reason,
            ))
            db.session.commit()
            return True

        except Exception as exception:
            db.session.rollback()
            raise exception

    def get_orders_by_user(self, user_id):
        """
        Retrieves orders associated with a user.

        Args:
        - user_id (int): ID of the user.

        Returns:
        - list: Serialized data of orders associated with the user.

        Raises:
        - Exception: If an error occurs during retrieval of user's orders.
        """
        try:
            orders = Order.query.filter_by(user_id=user_id).all()
            return [order.to_dict(include_items=False) for order in orders]
        except Exception as exception:
            raise exception

    def cancel_order(self, order_id, reason=None):
        """
        Cancels an order.

        Args:
        - order_id (int): ID of the order to cancel.

        Returns:
        - bool: True if order canceled successfully, otherwise False.

        Raises:
        - Exception: If an error occurs during order cancellation.
        """
        try:
            order = db.session.get(Order, order_id)
            if order:
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
            return False
        except Exception as exception:
            db.session.rollback()
            raise exception

    def get_orders_summary(self):
        """
        Returns order counts grouped by status.

        Returns:
        - dict: Mapping of status value to count.
        """
        from sqlalchemy import func
        results = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
        summary = {s.value: 0 for s in StatusEnum}
        for status, count in results:
            summary[status.value] = count
        return summary

    def bulk_update_status(self, order_ids, new_status):
        """
        Update status for multiple orders at once.

        Returns:
        - dict: counts of updated and skipped (terminal-state) orders.
        """
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
        except Exception as exception:
            db.session.rollback()
            raise exception

        return {"updated": updated, "skipped": skipped}

    def get_order_history(self, order_id):
        """Returns status transition history for an order, oldest first."""
        rows = (
            OrderStatusHistory.query
            .filter_by(order_id=order_id)
            .order_by(OrderStatusHistory.changed_at.asc())
            .all()
        )
        return [r.to_dict() for r in rows]

    def get_orders_by_status(self, status):
        """
        Retrieves orders by their status.

        Args:
        - status (str): Status of the orders to retrieve.

        Returns:
        - list: Serialized data of orders with the specified status.

        Raises:
        - Exception: If an error occurs during retrieval of orders by status.
        """
        try:
            orders = Order.query.filter_by(status=status.upper()).all()
            return [order.to_dict() for order in orders]
        except Exception as exception:
            raise exception


class OrderItemService:
    """
    A class handling various operations related to order items.
    """

    def update_order_item(self, order_id, item_id, quantity):
        """
        Update quantity of a single order item and recalculate total_price.

        Returns:
        - dict: updated item, or None if order/item not found.

        Raises:
        - ValueError: if the order is in a terminal state.
        """
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
        except Exception as exception:
            db.session.rollback()
            raise exception

        return item.to_dict()

    def get_order_items(self, order_id, product_id=None):
        """
        Retrieves all order items for a given order.

        Args:
        - order_id (int): ID of the order to retrieve items for.
        - product_id (int, optional): Filter by product ID.

        Returns:
        - list: Serialized data of order items for the specified order.

        Raises:
        - Exception: If an error occurs during retrieval of order items.
        """
        try:
            query = OrderItem.query.filter_by(order_id=order_id)
            if product_id is not None:
                query = query.filter_by(product_id=product_id)
            return [item.to_dict() for item in query.all()]
        except Exception as exception:
            raise exception
