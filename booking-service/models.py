from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_code = db.Column(db.String(50), nullable=False, unique=True)
    user_id = db.Column(db.Integer, nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum('pending', 'paid', 'cancelled'), default='pending')
    total_price = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    details = db.relationship('BookingDetail', backref='booking', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'booking_code': self.booking_code,
            'user_id': self.user_id,
            'booking_date': str(self.booking_date) if self.booking_date else None,
            'status': self.status,
            'total_price': self.total_price,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None,
            'BookingDetails': [d.to_dict() for d in self.details],
        }


class BookingDetail(db.Model):
    __tablename__ = 'booking_details'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    court_id = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, nullable=False)   # in hours

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'court_id': self.court_id,
            'start_time': str(self.start_time) if self.start_time else None,
            'end_time': str(self.end_time) if self.end_time else None,
            'duration': self.duration,
        }
