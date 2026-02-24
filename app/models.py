"""
Module containing database models for orders and order items.
"""

from datetime import datetime
from enum import Enum as PyEnum
from app import db

class StatusEnum(PyEnum):
    """Enumerates the status options for orders."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'

class Order(db.Model):
    """
    Represents an order in the database.
    """

    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float)
    items = db.relationship(
                'OrderItem',
                backref='order',
                cascade='all,delete-orphan',
                lazy='dynamic'
            )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(StatusEnum), default=StatusEnum.PENDING)

    def to_dict(self, include_items=True):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'total_price': self.total_price,
            'status': self.status.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
        return data

    def __repr__(self):
        return f"<Order id={self.id}, user_id={self.user_id}, " \
               f"total_price={self.total_price}, status='{self.status}'>"


class OrderItem(db.Model):
    """
    Represents an item within an order in the database.
    """

    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    product_id = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'price': self.price,
            'created_at': self.created_at,
        }

    def __repr__(self):
        return f"<OrderItem id={self.id}, order_id={self.order_id}, " \
               f"product_id={self.product_id}, quantity={self.quantity}, " \
               f"price={self.price}>"
