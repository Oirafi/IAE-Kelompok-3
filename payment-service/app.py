import os
import time
import jwt
import requests as http
import midtransclient
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Transaction

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

BOOKING_SERVICE_URL = os.getenv('BOOKING_SERVICE_URL', 'http://booking-service:3003')
JWT_SECRET = os.getenv('JWT_SECRET', 'supersecretkey')

snap = midtransclient.Snap(
    is_production=False,
    server_key=os.getenv('MIDTRANS_SERVER_KEY', ''),
    client_key=os.getenv('MIDTRANS_CLIENT_KEY', '')
)

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
    return {'status': 'OK', 'service': 'payment-service'}


@app.route('/create', methods=['POST'])
@authenticate
def create_payment():
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')

        try:
            booking_resp = http.get(
                f'{BOOKING_SERVICE_URL}/{booking_id}',
                headers={'Authorization': request.headers.get('Authorization')},
                timeout=5
            )
            booking = booking_resp.json()
        except Exception:
            return jsonify({'message': 'Failed to reach booking service'}), 503

        if booking_resp.status_code == 404:
            return jsonify({'message': 'Booking not found'}), 404

        transaction_code = f"TRX-{booking['booking_code']}-{int(time.time() * 1000)}"

        snap_response = snap.create_transaction({
            'transaction_details': {
                'order_id': transaction_code,
                'gross_amount': booking['total_price']
            },
            'customer_details': {'first_name': 'User', 'email': 'user@example.com'}
        })

        transaction = Transaction(
            booking_id=booking_id,
            transaction_code=transaction_code,
            snap_token=snap_response.get('token'),
            total_payment=booking['total_price'],
            payment_status='pending'
        )
        db.session.add(transaction)
        db.session.commit()

        return jsonify({
            'message': 'Payment transaction created',
            'transaction_id': transaction.id,
            'snap_token': snap_response.get('token'),
            'redirect_url': snap_response.get('redirect_url')
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/callback', methods=['POST'])
def payment_callback():
    # Midtrans webhook — no auth needed
    try:
        notification_data = request.get_json()
        status_response = snap.transaction_status(notification_data.get('order_id', ''))

        order_id = status_response.get('order_id')
        transaction_status = status_response.get('transaction_status')
        payment_type = status_response.get('payment_type')
        settlement_time = status_response.get('settlement_time')

        transaction = Transaction.query.filter_by(transaction_code=order_id).first()
        if not transaction:
            return jsonify({'message': 'Transaction not found'}), 404

        transaction.payment_status = transaction_status
        transaction.payment_type = payment_type
        if settlement_time:
            transaction.payment_time = datetime.fromisoformat(settlement_time)
        db.session.commit()

        if transaction_status in ('settlement', 'capture'):
            http.put(f'{BOOKING_SERVICE_URL}/{transaction.booking_id}', json={'status': 'paid'}, timeout=5)
        elif transaction_status in ('cancel', 'expire', 'deny'):
            http.put(f'{BOOKING_SERVICE_URL}/{transaction.booking_id}', json={'status': 'cancelled'}, timeout=5)

        return jsonify({'message': 'Callback processed'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/status/<int:transaction_id>', methods=['GET'])
@authenticate
def get_payment_status(transaction_id):
    try:
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'message': 'Transaction not found'}), 404
        return jsonify(transaction.to_dict()), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Payment database synced')
    PORT = int(os.getenv('PORT', 3005))
    print(f'payment-service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
