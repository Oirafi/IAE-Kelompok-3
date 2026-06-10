import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Court, CourtSchedule

load_dotenv()

# ─── App Setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/health')
def health():
    return {'status': 'OK', 'service': 'court-service'}


@app.route('/', methods=['GET'])
def get_all_courts():
    try:
        courts = Court.query.all()
        return jsonify([c.to_dict() for c in courts]), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/', methods=['POST'])
def create_court():
    try:
        data = request.get_json()
        court = Court(
            name=data.get('name'),
            description=data.get('description'),
            image=data.get('image'),
            price_per_hour=data.get('price_per_hour'),
            status=data.get('status', 'active')
        )
        db.session.add(court)
        db.session.commit()
        return jsonify(court.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:court_id>', methods=['GET'])
def get_court_by_id(court_id):
    try:
        court = Court.query.get(court_id)
        if not court:
            return jsonify({'message': 'Court not found'}), 404
        return jsonify(court.to_dict()), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:court_id>', methods=['PUT'])
def update_court(court_id):
    try:
        court = Court.query.get(court_id)
        if not court:
            return jsonify({'message': 'Court not found'}), 404
        data = request.get_json()
        for key, value in data.items():
            if hasattr(court, key):
                setattr(court, key, value)
        db.session.commit()
        return jsonify(court.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:court_id>', methods=['DELETE'])
def delete_court(court_id):
    try:
        court = Court.query.get(court_id)
        if not court:
            return jsonify({'message': 'Court not found'}), 404
        db.session.delete(court)
        db.session.commit()
        return jsonify({'message': 'Court deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Server error', 'error': str(e)}), 500


@app.route('/<int:court_id>/schedule', methods=['GET'])
def get_court_schedule(court_id):
    try:
        schedules = CourtSchedule.query.filter_by(court_id=court_id).all()
        return jsonify([s.to_dict() for s in schedules]), 200
    except Exception as e:
        return jsonify({'message': 'Server error', 'error': str(e)}), 500

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Court database synced')
    PORT = int(os.getenv('PORT', 3002))
    print(f'court-service running on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
