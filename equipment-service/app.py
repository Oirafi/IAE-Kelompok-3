import os
import jwt
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from models import serialize_doc, to_object_id

load_dotenv()

# ─── App Setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

# MongoDB Connection
MONGO_HOST = os.getenv('MONGO_HOST', 'mongo')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
MONGO_DB = os.getenv('MONGO_DB', 'equipment_db')

client = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
db = client[MONGO_DB]

equipments_col = db['equipments']
carts_col = db['carts']

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
        equipments = list(equipments_col.find())
        return jsonify([serialize_doc(e) for e in equipments]), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/', methods=['POST'])
def create_equipment():
    try:
        data = request.get_json()
        equipment = {
            'name': data.get('name'),
            'image': data.get('image'),
            'rental_price': data.get('rental_price') or data.get('price_per_hour'),
            'stock': data.get('stock', 0)
        }
        result = equipments_col.insert_one(equipment)
        equipment['_id'] = str(result.inserted_id)
        return jsonify(equipment), 201
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<equipment_id>', methods=['GET'])
def get_equipment_by_id(equipment_id):
    try:
        oid = to_object_id(equipment_id)
        if not oid:
            return jsonify({'message': 'Invalid equipment ID'}), 400
        equipment = equipments_col.find_one({'_id': oid})
        if not equipment:
            return jsonify({'message': 'Equipment not found'}), 404
        return jsonify(serialize_doc(equipment)), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<equipment_id>', methods=['PUT'])
def update_equipment(equipment_id):
    try:
        oid = to_object_id(equipment_id)
        if not oid:
            return jsonify({'message': 'Invalid equipment ID'}), 400
        data = request.get_json()
        update_fields = {k: v for k, v in data.items() if k != '_id'}
        result = equipments_col.update_one({'_id': oid}, {'$set': update_fields})
        if result.matched_count == 0:
            return jsonify({'message': 'Equipment not found'}), 404
        equipment = equipments_col.find_one({'_id': oid})
        return jsonify(serialize_doc(equipment)), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<equipment_id>', methods=['DELETE'])
def delete_equipment(equipment_id):
    try:
        oid = to_object_id(equipment_id)
        if not oid:
            return jsonify({'message': 'Invalid equipment ID'}), 400
        result = equipments_col.delete_one({'_id': oid})
        if result.deleted_count == 0:
            return jsonify({'message': 'Equipment not found'}), 404
        # Also remove cart items referencing this equipment
        carts_col.delete_many({'equipment_id': equipment_id})
        return jsonify({'message': 'Equipment deleted'}), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500

# ─── Cart Routes ───────────────────────────────────────────────────────────────

@app.route('/cart', methods=['GET'])
@authenticate
def get_cart():
    try:
        user_id = request.user['id']
        cart_items = list(carts_col.find({'user_id': user_id}))
        result = []
        for item in cart_items:
            item_dict = serialize_doc(item)
            # Populate equipment data
            equip_oid = to_object_id(item.get('equipment_id'))
            equipment = equipments_col.find_one({'_id': equip_oid}) if equip_oid else None
            item_dict['Equipment'] = serialize_doc(equipment) if equipment else None
            result.append(item_dict)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/cart', methods=['POST'])
@authenticate
def add_to_cart():
    try:
        data = request.get_json()
        equipment_id = data.get('equipment_id')
        quantity = data.get('quantity', 1)

        equip_oid = to_object_id(equipment_id)
        if not equip_oid:
            return jsonify({'message': 'Invalid equipment ID'}), 400

        equipment = equipments_col.find_one({'_id': equip_oid})
        if not equipment or equipment.get('stock', 0) < quantity:
            return jsonify({'message': 'Equipment out of stock or not found'}), 400

        user_id = request.user['id']
        existing = carts_col.find_one({'user_id': user_id, 'equipment_id': equipment_id})

        if existing:
            carts_col.update_one(
                {'_id': existing['_id']},
                {'$inc': {'quantity': quantity}}
            )
            existing = carts_col.find_one({'_id': existing['_id']})
            result = serialize_doc(existing)
        else:
            cart_item = {
                'user_id': user_id,
                'equipment_id': equipment_id,
                'quantity': quantity
            }
            insert_result = carts_col.insert_one(cart_item)
            cart_item['_id'] = str(insert_result.inserted_id)
            result = cart_item

        result['Equipment'] = serialize_doc(equipment)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/cart/<cart_id>', methods=['DELETE'])
@authenticate
def remove_from_cart(cart_id):
    try:
        oid = to_object_id(cart_id)
        if not oid:
            return jsonify({'message': 'Invalid cart ID'}), 400
        cart_item = carts_col.find_one({'_id': oid})
        if not cart_item or cart_item.get('user_id') != request.user['id']:
            return jsonify({'message': 'Item not found in cart'}), 404
        carts_col.delete_one({'_id': oid})
        return jsonify({'message': 'Item removed from cart'}), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f'Connected to MongoDB: {MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}')
    PORT = int(os.getenv('PORT', 3004))
    print(f'equipment-service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
