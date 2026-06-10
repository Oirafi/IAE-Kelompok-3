from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Court(db.Model):
    __tablename__ = 'courts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(500), nullable=True)
    price_per_hour = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum('active', 'maintenance'), default='active')

    schedules = db.relationship('CourtSchedule', backref='court', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'price_per_hour': self.price_per_hour,
            'status': self.status,
        }


class CourtSchedule(db.Model):
    __tablename__ = 'court_schedules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    court_id = db.Column(db.Integer, db.ForeignKey('courts.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False)   # "Monday", "Tuesday", etc.
    open_time = db.Column(db.Time, nullable=False)
    close_time = db.Column(db.Time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'court_id': self.court_id,
            'day': self.day,
            'open_time': str(self.open_time) if self.open_time else None,
            'close_time': str(self.close_time) if self.close_time else None,
        }
