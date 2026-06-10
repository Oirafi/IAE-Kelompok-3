import os
import jwt
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Equipment, Cart

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

# ─── Equipment Routes ──────────────────────────────────────────────────────────

@app.route('/health')
def health():
    return {'status': 'OK', 'service': 'equipment-service'}


@app.route('/', methods=['GET'])
def get_all_equipments():
    try:
        return jsonify([e.to_dict() for e in Equipment.query.all()]), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/', methods=['POST'])
def create_equipment():
    try:
        data = request.get_json()
        equipment = Equipment(
            name=data.get('name'),
            image=data.get('image'),
            rental_price=data.get('rental_price') or data.get('price_per_hour'),
            stock=data.get('stock', 0)
        )
        db.session.add(equipment)
        db.session.commit()
        return jsonify(equipment.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:equipment_id>', methods=['GET'])
def get_equipment_by_id(equipment_id):
    try:
        equipment = Equipment.query.get(equipment_id)
        if not equipment:
            return jsonify({'message': 'Equipment not found'}), 404
        return jsonify(equipment.to_dict()), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:equipment_id>', methods=['PUT'])
def update_equipment(equipment_id):
    try:
        equipment = Equipment.query.get(equipment_id)
        if not equipment:
            return jsonify({'message': 'Equipment not found'}), 404
        data = request.get_json()
        for key, value in data.items():
            if hasattr(equipment, key):
                setattr(equipment, key, value)
        db.session.commit()
        return jsonify(equipment.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:equipment_id>', methods=['DELETE'])
def delete_equipment(equipment_id):
    try:
        equipment = Equipment.query.get(equipment_id)
        if not equipment:
            return jsonify({'message': 'Equipment not found'}), 404
        db.session.delete(equipment)
        db.session.commit()
        return jsonify({'message': 'Equipment deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500

# ─── Cart Routes ───────────────────────────────────────────────────────────────

@app.route('/cart', methods=['GET'])
@authenticate
def get_cart():
    try:
        cart = Cart.query.filter_by(user_id=request.user['id']).all()
        return jsonify([c.to_dict() for c in cart]), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/cart', methods=['POST'])
@authenticate
def add_to_cart():
    try:
        data = request.get_json()
        equipment_id = data.get('equipment_id')
        quantity = data.get('quantity', 1)

        equipment = Equipment.query.get(equipment_id)
        if not equipment or equipment.stock < quantity:
            return jsonify({'message': 'Equipment out of stock or not found'}), 400

        cart_item = Cart.query.filter_by(user_id=request.user['id'], equipment_id=equipment_id).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = Cart(user_id=request.user['id'], equipment_id=equipment_id, quantity=quantity)
            db.session.add(cart_item)

        db.session.commit()
        return jsonify(cart_item.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/cart/<int:cart_id>', methods=['DELETE'])
@authenticate
def remove_from_cart(cart_id):
    try:
        cart_item = Cart.query.get(cart_id)
        if not cart_item or cart_item.user_id != request.user['id']:
            return jsonify({'message': 'Item not found in cart'}), 404
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({'message': 'Item removed from cart'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Equipment database synced')
    PORT = int(os.getenv('PORT', 3004))
    print(f'equipment-service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
