"""
Module Docstring: TestOrderEndpoints

This module contains unit tests for the endpoints related to orders in the application.
"""

import unittest
import json
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
