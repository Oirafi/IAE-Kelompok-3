from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_id = db.Column(db.Integer, nullable=False)
    transaction_code = db.Column(db.String(100), nullable=False, unique=True)
    snap_token = db.Column(db.String(255), nullable=True)
    payment_status = db.Column(
        db.Enum('pending', 'settlement', 'expire', 'cancel', 'deny'),
        default='pending'
    )
    payment_type = db.Column(db.String(50), nullable=True)
    total_payment = db.Column(db.Integer, nullable=False)
    payment_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'transaction_code': self.transaction_code,
            'snap_token': self.snap_token,
            'payment_status': self.payment_status,
            'payment_type': self.payment_type,
            'total_payment': self.total_payment,
            'payment_time': str(self.payment_time) if self.payment_time else None,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None,
        }
