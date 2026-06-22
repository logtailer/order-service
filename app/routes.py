"""Routes for the orders blueprint and app-level error handlers."""
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template
from sqlalchemy import text
from app import app, db
from app.models import StatusEnum
from app.services import (
    create_new_order,
    get_all_orders,
    get_order_by_id,
    update_order_status,
    get_orders_by_user,
    cancel_order,
    get_orders_by_status,
    get_orders_summary,
    bulk_update_status,
    update_order_notes,
    count_orders,
    get_order_history,
    get_order_items,
    update_order_item,
)

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health', methods=['GET'])
def health_check():
    """Health check including database connectivity status."""
    try:
        db.session.execute(text('SELECT 1'))
        db_status = 'connected'
    except Exception:
        db_status = 'disconnected'

    return jsonify({'status': 'healthy', 'db': db_status}), 200


@orders_bp.route('', methods=['POST'])
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

        order_id = create_new_order(order_data)
        return jsonify({"message": "New order created", "order_id": order_id}), 201

    except KeyError as exception:
        return jsonify({"error": f"Missing key: {str(exception)}"}), 400

    except Exception as exception:
        logging.error(f"Error processing order creation: {str(exception)}")
        return jsonify({"error": "An error occurred while processing the request"}), 500


@orders_bp.route('', methods=['GET'])
def get_orders():
    """Retrieve orders with optional pagination, filtering, and sorting."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        created_after = None
        created_before = None
        updated_after = None
        updated_before = None
        if request.args.get('created_after'):
            created_after = datetime.fromisoformat(request.args.get('created_after'))
        if request.args.get('created_before'):
            created_before = datetime.fromisoformat(request.args.get('created_before'))
        if request.args.get('updated_after'):
            updated_after = datetime.fromisoformat(request.args.get('updated_after'))
        if request.args.get('updated_before'):
            updated_before = datetime.fromisoformat(request.args.get('updated_before'))

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

        result = get_all_orders(
            page=page,
            per_page=per_page,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
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


@orders_bp.route('/bulk-status', methods=['PATCH'])
def bulk_update_order_status():
    """Update status for a list of order IDs in one request."""
    try:
        body = request.json
        if not body:
            return jsonify({"error": "No data provided"}), 400

        order_ids = body.get('order_ids')
        new_status = body.get('status')

        if not order_ids or not isinstance(order_ids, list):
            return jsonify({"error": "order_ids must be a non-empty list"}), 400
        if not new_status:
            return jsonify({"error": "status is required"}), 400

        valid_statuses = [
            StatusEnum.PENDING.value,
            StatusEnum.PROCESSING.value,
            StatusEnum.SHIPPED.value,
            StatusEnum.DELIVERED.value,
        ]
        if new_status.lower() not in valid_statuses:
            return jsonify({"error": "Invalid status provided"}), 400

        result = bulk_update_status(order_ids, new_status)
        return jsonify(result), 200

    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    """Get details of a specific order by order ID."""
    try:
        order = get_order_by_id(order_id)
        if order:
            return jsonify(order), 200
        return jsonify({"message": "Order not found"}), 404

    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/<int:order_id>', methods=['PATCH'])
def update_order_status_route(order_id):
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

        reason = status_data.get('reason')
        success = update_order_status(order_id, status_data, reason=reason)
        if success:
            return jsonify({"message": "Order status updated"}), 200
        return jsonify({"message": "Order not found"}), 404

    except ValueError as exception:
        return jsonify({"error": str(exception)}), 409
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/user/<int:user_id>', methods=['GET'])
def get_orders_by_user_route(user_id):
    """Get orders associated with a specific user."""
    try:
        orders = get_orders_by_user(user_id)
        return jsonify(orders), 200

    except Exception as exception:
        logging.exception("Error: %s", str(exception))
        return jsonify({"error": "An error occurred while processing the request"}), 500


@orders_bp.route('/<int:order_id>', methods=['DELETE'])
def cancel_order_route(order_id):
    """Cancel an order by order ID. Accepts optional JSON body with 'reason'."""
    try:
        body = request.get_json(silent=True) or {}
        reason = body.get('reason')
        success = cancel_order(order_id, reason=reason)
        if success:
            return jsonify({"message": "Order canceled"}), 200
        return jsonify({"message": "Order not found"}), 404

    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/status/<string:status>', methods=['GET'])
def get_orders_by_status_route(status):
    """Get orders by their status."""
    try:
        orders = get_orders_by_status(status)
        return jsonify(orders), 200

    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/<int:order_id>/notes', methods=['PATCH'])
def update_order_notes_route(order_id):
    """Set or clear the notes on an order."""
    try:
        body = request.get_json(silent=True) or {}
        notes = body.get('notes')
        success = update_order_notes(order_id, notes)
        if not success:
            return jsonify({"message": "Order not found"}), 404
        return jsonify({"message": "Notes updated"}), 200
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/count', methods=['GET'])
def get_orders_count():
    """Return the total number of orders, with optional status and user_id filters."""
    try:
        status = request.args.get('status')
        user_id = request.args.get('user_id', type=int)

        if status and status not in [s.value for s in StatusEnum]:
            return jsonify({"error": f"status must be one of: {', '.join(s.value for s in StatusEnum)}"}), 400

        count = count_orders(status=status, user_id=user_id)
        return jsonify({"count": count}), 200
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/summary', methods=['GET'])
def get_orders_summary_route():
    """Return order counts grouped by status."""
    try:
        summary = get_orders_summary()
        return jsonify(summary), 200
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/<int:order_id>/items', methods=['GET'])
def get_order_items_route(order_id):
    """Get all order items for a specific order, optionally filtered by product_id."""
    try:
        product_id = request.args.get('product_id', type=int)
        items = get_order_items(order_id, product_id=product_id)
        return jsonify(items), 200

    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/<int:order_id>/items/<int:item_id>', methods=['PATCH'])
def update_order_item_route(order_id, item_id):
    """Update the quantity of a specific order item."""
    try:
        body = request.get_json(silent=True) or {}
        quantity = body.get('quantity')

        if quantity is None:
            return jsonify({"error": "quantity is required"}), 400
        if not isinstance(quantity, int) or quantity <= 0:
            return jsonify({"error": "quantity must be a positive integer"}), 400

        result = update_order_item(order_id, item_id, quantity)
        if result is None:
            return jsonify({"message": "Order or item not found"}), 404
        return jsonify(result), 200

    except ValueError as exception:
        return jsonify({"error": str(exception)}), 409
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@orders_bp.route('/<int:order_id>/history', methods=['GET'])
def get_order_history_route(order_id):
    """Return the status transition history for an order."""
    try:
        order = get_order_by_id(order_id)
        if not order:
            return jsonify({"message": "Order not found"}), 404
        history = get_order_history(order_id)
        return jsonify(history), 200
    except Exception as exception:
        return jsonify({"error": str(exception)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "method not allowed"}), 405
