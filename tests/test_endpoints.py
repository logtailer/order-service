"""
Module Docstring: TestOrderEndpoints

This module contains unit tests for the endpoints related to orders in the application.
"""

import unittest
import json
from datetime import datetime
from app import app, db
from app.models import Order, OrderItem, StatusEnum

class TestOrderEndpoints(unittest.TestCase):
    """
    TestOrderEndpoints Class

    This class contains unit tests for various endpoints related to orders in the application.
    """
    def setUp(self):
        """ Set up test environment """
        self.app = app.test_client()

        with app.app_context():
            app.config['TESTING'] = True
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
            db.create_all()

    def tearDown(self):
        """ Remove test environment """
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_health_check(self):
        """ Test the health check endpoint """
        with app.app_context():
            response = self.app.get('/health')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['status'], 'healthy')

    def test_create_order(self):
        """ Test creating a new order """
        with app.app_context():
            order_data = {
                'user_id': 1,
                'status': 'pending',
                'items': [
                    {'product_id': 1, 'quantity': 2, 'price': 10.0},
                    {'product_id': 2, 'quantity': 1, 'price': 20.0}
                ]
            }

            response = self.app.post('/orders', json=order_data)
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 201)
            self.assertTrue(data['order_id'])

            created_order = db.session.get(Order, data['order_id'])
            self.assertIsNotNone(created_order)
            self.assertEqual(created_order.user_id, order_data['user_id'])
            self.assertEqual(created_order.status, StatusEnum.PENDING)

            self.assertEqual(created_order.items.count(), 2)

    def test_get_orders(self):
        """ Test retrieving all orders returns paginated response """
        with app.app_context():
            order1 = Order(user_id=1, total_price=50.0, status=StatusEnum.SHIPPED)
            order2 = Order(user_id=2, total_price=30.0, status=StatusEnum.PENDING)
            db.session.add(order1)
            db.session.add(order2)
            db.session.commit()

            response = self.app.get('/orders')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertIn('orders', data)
            self.assertIn('total', data)
            self.assertIn('page', data)
            self.assertIn('pages', data)
            self.assertGreater(data['total'], 0)

    def test_get_orders_pagination(self):
        """ Test pagination limits returned results """
        with app.app_context():
            for i in range(5):
                db.session.add(Order(user_id=i, total_price=10.0, status=StatusEnum.PENDING))
            db.session.commit()

            response = self.app.get('/orders?page=1&per_page=2')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data['orders']), 2)
            self.assertEqual(data['per_page'], 2)
            self.assertEqual(data['total'], 5)

    def test_get_orders_date_filter(self):
        """ Test filtering orders by created_after """
        with app.app_context():
            from datetime import datetime, timedelta
            old_order = Order(user_id=1, total_price=10.0, status=StatusEnum.PENDING)
            old_order.created_at = datetime(2025, 1, 1)
            new_order = Order(user_id=2, total_price=20.0, status=StatusEnum.PENDING)
            new_order.created_at = datetime(2026, 1, 1)
            db.session.add(old_order)
            db.session.add(new_order)
            db.session.commit()

            response = self.app.get('/orders?created_after=2025-06-01T00:00:00')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['total'], 1)
            self.assertEqual(data['orders'][0]['user_id'], 2)

    def test_get_order_details(self):
        """ Test retrieving details of a specific order by order ID """
        with app.app_context():
            order = Order(user_id=1, total_price=50.0, status=StatusEnum.SHIPPED)
            db.session.add(order)
            db.session.commit()

            order_id = order.id

            response = self.app.get(f'/orders/{order_id}')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['id'], order_id)

    def test_update_order_status(self):
        """ Test updating the status of an order by order ID """
        with app.app_context():
            order = Order(user_id=1, total_price=50.0, status=StatusEnum.PENDING)
            db.session.add(order)
            db.session.commit()

            order_id = order.id
            new_status_data = {'status': 'shipped'}

            response = self.app.patch(f'/orders/{order_id}', json=new_status_data)
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['message'], 'Order status updated')

            updated_order = db.session.get(Order, order_id)
            self.assertEqual(updated_order.status, StatusEnum.SHIPPED)

    def test_get_orders_by_user(self):
        """ Test retrieving orders associated with a specific user """
        with app.app_context():
            user_id = 1
            order1 = Order(user_id=user_id, total_price=50.0, status='SHIPPED')
            order2 = Order(user_id=user_id, total_price=30.0, status='PENDING')
            db.session.add(order1)
            db.session.add(order2)
            db.session.commit()

            response = self.app.get(f'/orders/user/{user_id}')

            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(data, list)

    def test_cancel_order(self):
        """ Test canceling an order marks it as CANCELLED rather than deleting it """
        with app.app_context():
            order = Order(user_id=1, total_price=50.0, status=StatusEnum.PENDING)
            db.session.add(order)
            db.session.commit()

            order_id = order.id

            response = self.app.delete(f'/orders/{order_id}')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['message'], 'Order canceled')

            cancelled_order = db.session.get(Order, order_id)
            self.assertIsNotNone(cancelled_order)
            self.assertEqual(cancelled_order.status, StatusEnum.CANCELLED)

    def test_update_order_to_delivered(self):
        """ Test updating an order status to delivered """
        with app.app_context():
            order = Order(user_id=1, total_price=75.0, status=StatusEnum.SHIPPED)
            db.session.add(order)
            db.session.commit()

            order_id = order.id
            response = self.app.patch(f'/orders/{order_id}', json={'status': 'delivered'})
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['message'], 'Order status updated')

            updated_order = db.session.get(Order, order_id)
            self.assertEqual(updated_order.status, StatusEnum.DELIVERED)

    def test_get_orders_by_status(self):
        """ Test retrieving orders by their status """
        with app.app_context():
            # Assuming orders with a specific status exist in the database
            # Create sample orders with a specific status for testing
            status = StatusEnum.PENDING.value
            order1 = Order(user_id=1, total_price=50.0, status=status)
            order2 = Order(user_id=2, total_price=30.0, status=status)
            db.session.add(order1)
            db.session.add(order2)
            db.session.commit()

            response = self.app.get(f'/orders/status/{status}')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(data, list)

    def test_get_order_items(self):
        """ Test retrieving all order items for a specific order """
        with app.app_context():
            order_id = 1
            item1 = OrderItem(order_id=order_id, product_id=1, quantity=2, price=10.0)
            item2 = OrderItem(order_id=order_id, product_id=2, quantity=1, price=20.0)
            db.session.add(item1)
            db.session.add(item2)
            db.session.commit()

            response = self.app.get(f'/orders/{order_id}/items')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(data, list)

    def test_get_order_items_filter_by_product_id(self):
        """ Test filtering order items by product_id """
        with app.app_context():
            order = Order(user_id=1, total_price=60.0, status=StatusEnum.PENDING)
            db.session.add(order)
            db.session.flush()

            db.session.add(OrderItem(order_id=order.id, product_id=10, quantity=1, price=20.0))
            db.session.add(OrderItem(order_id=order.id, product_id=20, quantity=2, price=15.0))
            db.session.add(OrderItem(order_id=order.id, product_id=10, quantity=1, price=10.0))
            db.session.commit()

            response = self.app.get(f'/orders/{order.id}/items?product_id=10')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 2)
            for item in data:
                self.assertEqual(item['product_id'], 10)

    def test_get_order_items_product_id_no_match(self):
        """ Test product_id filter returns empty list when no items match """
        with app.app_context():
            order = Order(user_id=1, total_price=20.0, status=StatusEnum.PENDING)
            db.session.add(order)
            db.session.flush()
            db.session.add(OrderItem(order_id=order.id, product_id=5, quantity=1, price=20.0))
            db.session.commit()

            response = self.app.get(f'/orders/{order.id}/items?product_id=99')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data, [])

    def test_health_check_includes_db_status(self):
        """ Test that health check returns db connectivity status """
        with app.app_context():
            response = self.app.get('/health')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertIn('db', data)
            self.assertEqual(data['db'], 'connected')

    def test_create_order_rejects_zero_quantity(self):
        """ Test that order creation fails when item quantity is zero """
        with app.app_context():
            order_data = {
                'user_id': 1,
                'status': 'pending',
                'items': [{'product_id': 1, 'quantity': 0, 'price': 10.0}]
            }
            response = self.app.post('/orders', json=order_data)
            self.assertEqual(response.status_code, 400)

    def test_create_order_rejects_negative_price(self):
        """ Test that order creation fails when item price is negative """
        with app.app_context():
            order_data = {
                'user_id': 1,
                'status': 'pending',
                'items': [{'product_id': 1, 'quantity': 2, 'price': -5.0}]
            }
            response = self.app.post('/orders', json=order_data)
            self.assertEqual(response.status_code, 400)

    def test_update_terminal_order_returns_409(self):
        """ Test that updating a CANCELLED order returns 409 """
        with app.app_context():
            order = Order(user_id=1, total_price=50.0, status=StatusEnum.CANCELLED)
            db.session.add(order)
            db.session.commit()

            response = self.app.patch(f'/orders/{order.id}', json={'status': 'pending'})
            self.assertEqual(response.status_code, 409)

    def test_get_orders_summary(self):
        """ Test that summary endpoint returns counts per status """
        with app.app_context():
            db.session.add(Order(user_id=1, total_price=10.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=2, total_price=20.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=3, total_price=30.0, status=StatusEnum.SHIPPED))
            db.session.commit()

            response = self.app.get('/orders/summary')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['pending'], 2)
            self.assertEqual(data['shipped'], 1)
            self.assertIn('delivered', data)
            self.assertIn('cancelled', data)

    def test_get_orders_sort_by_total_price_asc(self):
        """ Test sorting orders by total_price ascending """
        with app.app_context():
            db.session.add(Order(user_id=1, total_price=100.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=2, total_price=10.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=3, total_price=50.0, status=StatusEnum.PENDING))
            db.session.commit()

            response = self.app.get('/orders?sort_by=total_price&sort_order=asc')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            prices = [o['total_price'] for o in data['orders']]
            self.assertEqual(prices, sorted(prices))

    def test_get_orders_invalid_sort_field(self):
        """ Test that an unknown sort_by value returns 400 """
        with app.app_context():
            response = self.app.get('/orders?sort_by=user_id')
            self.assertEqual(response.status_code, 400)

    def test_get_orders_filter_by_status(self):
        """ Test filtering orders by status query param """
        with app.app_context():
            db.session.add(Order(user_id=1, total_price=20.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=2, total_price=30.0, status=StatusEnum.SHIPPED))
            db.session.add(Order(user_id=3, total_price=40.0, status=StatusEnum.SHIPPED))
            db.session.commit()

            response = self.app.get('/orders?status=shipped')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['total'], 2)
            for order in data['orders']:
                self.assertEqual(order['status'], 'shipped')

    def test_get_orders_filter_by_user_id(self):
        """ Test filtering orders by user_id query param """
        with app.app_context():
            db.session.add(Order(user_id=7, total_price=15.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=7, total_price=25.0, status=StatusEnum.PROCESSING))
            db.session.add(Order(user_id=9, total_price=10.0, status=StatusEnum.PENDING))
            db.session.commit()

            response = self.app.get('/orders?user_id=7')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['total'], 2)
            for order in data['orders']:
                self.assertEqual(order['user_id'], 7)

    def test_get_orders_filter_by_status_and_user_id(self):
        """ Test combining status and user_id filters """
        with app.app_context():
            db.session.add(Order(user_id=5, total_price=10.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=5, total_price=20.0, status=StatusEnum.SHIPPED))
            db.session.add(Order(user_id=6, total_price=30.0, status=StatusEnum.PENDING))
            db.session.commit()

            response = self.app.get('/orders?user_id=5&status=pending')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['total'], 1)
            self.assertEqual(data['orders'][0]['user_id'], 5)
            self.assertEqual(data['orders'][0]['status'], 'pending')

    def test_get_orders_invalid_status_filter(self):
        """ Test that an unknown status value returns 400 """
        with app.app_context():
            response = self.app.get('/orders?status=bogus')
            self.assertEqual(response.status_code, 400)

    def test_get_orders_filter_by_updated_after(self):
        """ Test filtering orders updated after a given timestamp """
        with app.app_context():
            from datetime import timedelta
            now = datetime.utcnow()
            old = Order(user_id=1, total_price=10.0, status=StatusEnum.PENDING)
            old.updated_at = now - timedelta(days=5)
            recent = Order(user_id=2, total_price=20.0, status=StatusEnum.PENDING)
            recent.updated_at = now - timedelta(hours=1)
            db.session.add_all([old, recent])
            db.session.commit()

            cutoff = (now - timedelta(days=1)).isoformat()
            response = self.app.get(f'/orders?updated_after={cutoff}')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['total'], 1)

    def test_get_orders_filter_by_updated_before(self):
        """ Test filtering orders updated before a given timestamp """
        with app.app_context():
            from datetime import timedelta
            now = datetime.utcnow()
            old = Order(user_id=1, total_price=10.0, status=StatusEnum.PENDING)
            old.updated_at = now - timedelta(days=5)
            recent = Order(user_id=2, total_price=20.0, status=StatusEnum.PENDING)
            recent.updated_at = now - timedelta(hours=1)
            db.session.add_all([old, recent])
            db.session.commit()

            cutoff = (now - timedelta(days=2)).isoformat()
            response = self.app.get(f'/orders?updated_before={cutoff}')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['total'], 1)

    def test_get_orders_filter_by_min_price(self):
        """ Test filtering orders with min_price """
        with app.app_context():
            db.session.add(Order(user_id=1, total_price=10.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=2, total_price=50.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=3, total_price=200.0, status=StatusEnum.PENDING))
            db.session.commit()

            response = self.app.get('/orders?min_price=40')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['total'], 2)
            for order in data['orders']:
                self.assertGreaterEqual(order['total_price'], 40)

    def test_get_orders_filter_by_max_price(self):
        """ Test filtering orders with max_price """
        with app.app_context():
            db.session.add(Order(user_id=1, total_price=10.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=2, total_price=50.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=3, total_price=200.0, status=StatusEnum.PENDING))
            db.session.commit()

            response = self.app.get('/orders?max_price=50')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['total'], 2)
            for order in data['orders']:
                self.assertLessEqual(order['total_price'], 50)

    def test_get_orders_filter_by_price_range(self):
        """ Test filtering orders with both min_price and max_price """
        with app.app_context():
            db.session.add(Order(user_id=1, total_price=10.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=2, total_price=75.0, status=StatusEnum.PENDING))
            db.session.add(Order(user_id=3, total_price=200.0, status=StatusEnum.PENDING))
            db.session.commit()

            response = self.app.get('/orders?min_price=20&max_price=100')
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['total'], 1)
            self.assertEqual(data['orders'][0]['total_price'], 75.0)


class TestOrderStatusHistory(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_order(self):
        response = self.app.post('/orders', json={
            'user_id': 1, 'status': 'pending',
            'items': [{'product_id': 1, 'quantity': 1, 'price': 10.0}],
        })
        return json.loads(response.data)['order_id']

    def test_history_created_on_order_creation(self):
        """ Test that a history entry is written when an order is created """
        order_id = self._create_order()
        response = self.app.get(f'/orders/{order_id}/history')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 1)
        self.assertIsNone(data[0]['from_status'])
        self.assertEqual(data[0]['to_status'], 'pending')

    def test_history_grows_on_status_update(self):
        """ Test that each status update appends to history """
        order_id = self._create_order()
        self.app.patch(f'/orders/{order_id}', json={'status': 'processing'})
        self.app.patch(f'/orders/{order_id}', json={'status': 'shipped'})

        response = self.app.get(f'/orders/{order_id}/history')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 3)
        self.assertEqual(data[1]['from_status'], 'pending')
        self.assertEqual(data[1]['to_status'], 'processing')
        self.assertEqual(data[2]['from_status'], 'processing')
        self.assertEqual(data[2]['to_status'], 'shipped')

    def test_history_on_cancel(self):
        """ Test that cancellation writes a history entry """
        order_id = self._create_order()
        self.app.delete(f'/orders/{order_id}')

        response = self.app.get(f'/orders/{order_id}/history')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(len(data), 2)
        self.assertEqual(data[-1]['to_status'], 'cancelled')

    def test_history_404_for_unknown_order(self):
        """ Test that history endpoint returns 404 for missing order """
        response = self.app.get('/orders/9999/history')
        self.assertEqual(response.status_code, 404)

    def test_cancellation_reason_stored_in_history(self):
        """ Test that reason passed to DELETE is persisted in history """
        order_id = self._create_order()
        self.app.delete(f'/orders/{order_id}', json={'reason': 'customer request'})

        response = self.app.get(f'/orders/{order_id}/history')
        data = json.loads(response.data.decode('utf-8'))

        cancel_entry = data[-1]
        self.assertEqual(cancel_entry['to_status'], 'cancelled')
        self.assertEqual(cancel_entry['reason'], 'customer request')

    def test_cancellation_without_reason_stores_null(self):
        """ Test that omitting reason stores null in history """
        order_id = self._create_order()
        self.app.delete(f'/orders/{order_id}')

        response = self.app.get(f'/orders/{order_id}/history')
        data = json.loads(response.data.decode('utf-8'))

        self.assertIsNone(data[-1]['reason'])


class TestBulkStatusUpdate(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_bulk_update_updates_eligible_orders(self):
        """ Test that eligible orders get their status updated """
        with app.app_context():
            o1 = Order(user_id=1, total_price=10.0, status=StatusEnum.PENDING)
            o2 = Order(user_id=2, total_price=20.0, status=StatusEnum.PENDING)
            db.session.add_all([o1, o2])
            db.session.commit()
            ids = [o1.id, o2.id]

        response = self.app.patch('/orders/bulk-status', json={'order_ids': ids, 'status': 'processing'})
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(data['updated']), sorted(ids))
        self.assertEqual(data['skipped'], [])

    def test_bulk_update_skips_terminal_orders(self):
        """ Test that delivered/cancelled orders are skipped """
        with app.app_context():
            o1 = Order(user_id=1, total_price=10.0, status=StatusEnum.PENDING)
            o2 = Order(user_id=2, total_price=20.0, status=StatusEnum.DELIVERED)
            db.session.add_all([o1, o2])
            db.session.commit()
            ids = [o1.id, o2.id]

        response = self.app.patch('/orders/bulk-status', json={'order_ids': ids, 'status': 'shipped'})
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['updated']), 1)
        self.assertEqual(len(data['skipped']), 1)

    def test_bulk_update_missing_order_ids(self):
        """ Test validation when order_ids is absent """
        response = self.app.patch('/orders/bulk-status', json={'status': 'shipped'})
        self.assertEqual(response.status_code, 400)

    def test_bulk_update_invalid_status(self):
        """ Test validation when status value is invalid """
        response = self.app.patch('/orders/bulk-status', json={'order_ids': [1], 'status': 'bogus'})
        self.assertEqual(response.status_code, 400)

    def test_bulk_update_skips_nonexistent_orders(self):
        """ Test that non-existent order ids land in skipped """
        response = self.app.patch('/orders/bulk-status', json={'order_ids': [9999], 'status': 'shipped'})
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(9999, data['skipped'])


class TestAuthMiddleware(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_request_rejected_without_api_key(self):
        """ Test that requests are rejected when API_KEY env var is set """
        import os
        os.environ['API_KEY'] = 'secret-key'
        try:
            response = self.app.get('/orders')
            self.assertEqual(response.status_code, 401)
        finally:
            del os.environ['API_KEY']

    def test_request_accepted_with_valid_api_key(self):
        """ Test that requests succeed with correct API key header """
        import os
        os.environ['API_KEY'] = 'secret-key'
        try:
            response = self.app.get('/orders', headers={'X-API-Key': 'secret-key'})
            self.assertEqual(response.status_code, 200)
        finally:
            del os.environ['API_KEY']

    def test_request_rejected_with_wrong_api_key(self):
        """ Test that wrong API key returns 401 """
        import os
        os.environ['API_KEY'] = 'secret-key'
        try:
            response = self.app.get('/orders', headers={'X-API-Key': 'wrong'})
            self.assertEqual(response.status_code, 401)
        finally:
            del os.environ['API_KEY']

    def test_health_check_bypasses_auth(self):
        """ Test that /health does not require API key """
        import os
        os.environ['API_KEY'] = 'secret-key'
        try:
            response = self.app.get('/health')
            self.assertEqual(response.status_code, 200)
        finally:
            del os.environ['API_KEY']

    def test_no_auth_required_when_api_key_not_configured(self):
        """ Test that auth is skipped when API_KEY is not set """
        import os
        os.environ.pop('API_KEY', None)
        response = self.app.get('/orders')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
