import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect, url_for
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from models import db, User

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

# ─── Google OAuth ─────────────────────────────────────────────────────────────

oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

JWT_SECRET = os.getenv('JWT_SECRET', 'supersecretkey')


def generate_token(user):
    payload = {
        'id': user.id,
        'role': user.role,
        'exp': datetime.now(timezone.utc) + timedelta(days=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


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
    return {'status': 'OK', 'service': 'auth-service'}


@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name, email, password, phone = data.get('name'), data.get('email'), data.get('password'), data.get('phone')

        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'Email already in use'}), 400

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(name=name, email=email, password=hashed, phone=phone)
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully', 'user': {'id': user.id, 'name': user.name, 'email': user.email}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data.get('email')).first()
        if not user:
            return jsonify({'message': 'User not found'}), 404
        if not user.password:
            return jsonify({'message': 'Please login using Google'}), 400
        if not bcrypt.checkpw(data.get('password').encode(), user.password.encode()):
            return jsonify({'message': 'Invalid credentials'}), 401

        token = generate_token(user)
        return jsonify({'message': 'Login successful', 'token': token,
                        'user': {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}}), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/profile', methods=['GET'])
@authenticate
def get_profile():
    try:
        user = User.query.get(request.user['id'])
        if not user:
            return jsonify({'message': 'User not found'}), 404
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/profile', methods=['PUT'])
@authenticate
def update_profile():
    try:
        data = request.get_json()
        user = User.query.get(request.user['id'])
        if not user:
            return jsonify({'message': 'User not found'}), 404
        for field in ('name', 'phone', 'avatar'):
            if field in data:
                setattr(user, field, data[field])
        db.session.commit()
        return jsonify({'message': 'Profile updated'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


# ─── Google OAuth Routes ───────────────────────────────────────────────────────

@app.route('/google')
def google_login():
    redirect_uri = url_for('google_authorized', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/google/callback')
def google_authorized():
    try:
        token = oauth.google.authorize_access_token()
        profile = token.get('userinfo')
        if not profile:
            return jsonify({'message': 'Failed to fetch Google profile'}), 400

        google_id, email = profile['sub'], profile['email']
        user = User.query.filter_by(google_id=google_id).first()

        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.google_id = google_id
            else:
                user = User(name=profile.get('name', ''), email=email,
                            google_id=google_id, avatar=profile.get('picture', ''))
                db.session.add(user)
            db.session.commit()

        jwt_token = generate_token(user)
        return redirect(f'http://localhost:3000?token={jwt_token}')
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Database synced')
    PORT = int(os.getenv('PORT', 3001))
    print(f'auth-service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
