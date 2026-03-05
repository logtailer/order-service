"""
This module contains routes for managing orders.

Endpoints:
- GET /health: Health check endpoint returning a success status.
- POST /orders: Create a new order.
- GET /orders: Retrieve all orders.
- GET /orders/<int:order_id>: Get details of a specific order by order ID.
- PATCH /orders/<int:order_id>: Update the status of an order by order ID.
- GET /orders/user/<int:user_id>: Get orders associated with a specific user.
- DELETE /orders/<int:order_id>: Cancel an order by order ID.
- GET /orders/status/<string:status>: Get orders by their status.
- GET /orders/<int:order_id>/items: Get all order items for a specific order.
"""
import logging
from datetime import datetime
from flask import jsonify, request
from sqlalchemy import text
from app.services import OrderService, OrderItemService
from app import app, db
from app.models import StatusEnum

order_service = OrderService()
order_item_service = OrderItemService()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check including database connectivity status."""
    try:
        db.session.execute(text('SELECT 1'))
        db_status = 'connected'
    except Exception:
        db_status = 'disconnected'

    return jsonify({'status': 'healthy', 'db': db_status}), 200

@app.route('/orders', methods=['POST'])
def create_order():
    """Create a new order."""
    try:
        order_data = request.json
        if not order_data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['user_id', 'status', 'items']
        for field in required_fields:
            if field not in order_data:
                return jsonify({"error": f"Missing '{field}' field"}), 400

        status = order_data['status'].lower()

        valid_statuses = [
            StatusEnum.PENDING.value,
            StatusEnum.PROCESSING.value,
            StatusEnum.SHIPPED.value
        ]

        if status not in valid_statuses:
            return jsonify({"error": "Invalid status provided"}), 400

        for item in order_data.get('items', []):
            if not item.get('quantity') or item['quantity'] <= 0:
                return jsonify({"error": "Item quantity must be greater than 0"}), 400
            if not item.get('price') or item['price'] <= 0:
                return jsonify({"error": "Item price must be greater than 0"}), 400

        order_id = order_service.create_new_order(order_data)
        return jsonify({"message": "New order created", "order_id": order_id}), 201

    except KeyError as exception:
        return jsonify({"error": f"Missing key: {str(exception)}"}), 400

    except Exception as exception:
        logging.error(f"Error processing order creation: {str(exception)}")
        return jsonify({"error": "An error occurred while processing the request"}), 500

@app.route('/orders', methods=['GET'])
def get_orders():
    """Route to retrieve orders with optional pagination and date filtering."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        created_after = None
        created_before = None
        if request.args.get('created_after'):
            created_after = datetime.fromisoformat(request.args.get('created_after'))
        if request.args.get('created_before'):
            created_before = datetime.fromisoformat(request.args.get('created_before'))

        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        status = request.args.get('status')
        user_id = request.args.get('user_id', type=int)
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)

        valid_sort_fields = ['created_at', 'updated_at', 'total_price']
        if sort_by not in valid_sort_fields:
            return jsonify({"error": f"sort_by must be one of: {', '.join(valid_sort_fields)}"}), 400
        if sort_order not in ('asc', 'desc'):
            return jsonify({"error": "sort_order must be 'asc' or 'desc'"}), 400
        if status and status not in [s.value for s in StatusEnum]:
            return jsonify({"error": f"status must be one of: {', '.join(s.value for s in StatusEnum)}"}), 400

        result = order_service.get_all_orders(
            page=page,
            per_page=per_page,
            created_after=created_after,
            created_before=created_before,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
            user_id=user_id,
            min_price=min_price,
            max_price=max_price,
        )
        return jsonify(result), 200
    except ValueError:
        return jsonify({"error": "Invalid date format, use ISO 8601"}), 400
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500

@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    """Get details of a specific order by order ID."""
    try:
        order = order_service.get_order_by_id(order_id)
        if order:
            return jsonify(order), 200
        return jsonify({"message": "Order not found"}), 404

    except Exception as exception:
        return jsonify({"error": str(exception)}), 500

@app.route('/orders/<int:order_id>', methods=['PATCH'])
def update_order_status(order_id):
    """Update the status of an order by order ID."""
    try:
        status_data = request.json
        if not status_data:
            return jsonify({"error": "No data provided"}), 400

        new_status = status_data.get('status').lower()

        if not new_status:
            return jsonify({"error": "Incomplete data provided"}), 400

        valid_statuses = [
            StatusEnum.PENDING.value,
            StatusEnum.PROCESSING.value,
            StatusEnum.SHIPPED.value,
            StatusEnum.DELIVERED.value,
        ]

        if new_status not in valid_statuses:
            return jsonify({"error": "Invalid status provided"}), 400

        success = order_service.update_order_status(order_id, status_data)
        if success:
            return jsonify({"message": "Order status updated"}), 200
        return jsonify({"message": "Order not found"}), 404

    except ValueError as exception:
        return jsonify({"error": str(exception)}), 409
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500

@app.route('/orders/user/<int:user_id>', methods=['GET'])
def get_orders_by_user(user_id):
    """Get orders associated with a specific user."""
    try:
        orders = order_service.get_orders_by_user(user_id)
        return jsonify(orders), 200

    except Exception as exception:
        logging.exception("Error: %s", str(exception))
        return jsonify({"error": "An error occurred while processing the request"}), 500

@app.route('/orders/<int:order_id>', methods=['DELETE'])
def cancel_order(order_id):
    """Cancel an order by order ID."""
    try:
        success = order_service.cancel_order(order_id)
        if success:
            return jsonify({"message": "Order canceled"}), 200
        return jsonify({"message": "Order not found"}), 404

    except Exception as exception:
        return jsonify({"error": str(exception)}), 500

@app.route('/orders/status/<string:status>', methods=['GET'])
def get_orders_by_status(status):
    """Get orders by their status."""
    try:
        orders = order_service.get_orders_by_status(status)
        return jsonify(orders), 200

    except Exception as exception:
        return jsonify({"error": str(exception)}), 500

@app.route('/orders/summary', methods=['GET'])
def get_orders_summary():
    """Return order counts grouped by status."""
    try:
        summary = order_service.get_orders_summary()
        return jsonify(summary), 200
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500

@app.route('/orders/<int:order_id>/items', methods=['GET'])
def get_order_items(order_id):
    """Get all order items for a specific order."""
    try:
        items = order_item_service.get_order_items(order_id)
        return jsonify(items), 200

    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "method not allowed"}), 405
