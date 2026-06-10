import os
import secrets
import jwt
import requests as http
from datetime import datetime, timedelta, timezone
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Booking, BookingDetail

load_dotenv()

# ─── App Setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'supersecretkey')

db.init_app(app)

COURT_SERVICE_URL = os.getenv('COURT_SERVICE_URL', 'http://court-service:3002')
JWT_SECRET = os.getenv('JWT_SECRET', 'supersecretkey')

# ─── JWT Middleware ────────────────────────────────────────────────────────────

def authenticate(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        parts = auth_header.split(' ')
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'message': 'Access denied. No token provided.'}), 401
        try:
            decoded = jwt.decode(parts[1], JWT_SECRET, algorithms=['HS256'])
            request.user = decoded
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token.'}), 400
        return f(*args, **kwargs)
    return decorated

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/health')
def health():
    return {'status': 'OK', 'service': 'booking-service'}


@app.route('/', methods=['POST'])
@authenticate
def create_booking():
    try:
        data = request.get_json()
        court_id = data.get('court_id')
        booking_date = data.get('booking_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        duration = data.get('duration')
        user_id = request.user['id']

        # Calculate duration if not provided
        if not duration and start_time and end_time:
            fmt = '%H:%M:%S' if len(start_time) > 5 else '%H:%M'
            start = datetime.strptime(start_time, fmt)
            end = datetime.strptime(end_time, fmt)
            duration = int((end - start).seconds / 3600)

        # 1. Get court details from court-service
        try:
            court_resp = http.get(f'{COURT_SERVICE_URL}/{court_id}', timeout=5)
            court = court_resp.json()
        except Exception:
            return jsonify({'message': 'Failed to reach court service'}), 503

        if court_resp.status_code == 404:
            return jsonify({'message': 'Court not found'}), 404

        # 2. Check availability
        existing = (
            BookingDetail.query.join(Booking)
            .filter(
                Booking.booking_date == booking_date,
                Booking.status.in_(['pending', 'paid']),
                BookingDetail.court_id == court_id,
                BookingDetail.start_time == start_time,
            ).first()
        )
        if existing:
            return jsonify({'message': 'Court is not available for this time slot'}), 400

        # 3. Create booking
        total_price = court['price_per_hour'] * duration
        booking_code = 'BKG-' + secrets.token_hex(4).upper()

        booking = Booking(
            booking_code=booking_code, user_id=user_id,
            booking_date=booking_date, total_price=total_price, status='pending'
        )
        db.session.add(booking)
        db.session.flush()

        detail = BookingDetail(
            booking_id=booking.id, court_id=court_id,
            start_time=start_time, end_time=end_time, duration=duration
        )
        db.session.add(detail)
        db.session.commit()
        return jsonify({'message': 'Booking created successfully', 'booking': booking.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/', methods=['GET'])
@authenticate
def get_all_bookings():
    try:
        return jsonify([b.to_dict() for b in Booking.query.all()]), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:booking_id>', methods=['GET'])
@authenticate
def get_booking_by_id(booking_id):
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        return jsonify(booking.to_dict()), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:booking_id>', methods=['PUT'])
def update_booking_status(booking_id):
    # No auth — called internally by payment-service
    try:
        data = request.get_json()
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        booking.status = data.get('status')
        db.session.commit()
        return jsonify({'message': 'Booking status updated', 'booking': booking.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:booking_id>', methods=['DELETE'])
@authenticate
def delete_booking(booking_id):
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        db.session.delete(booking)
        db.session.commit()
        return jsonify({'message': 'Booking deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Booking database synced')
    PORT = int(os.getenv('PORT', 3003))
    print(f'booking-service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
