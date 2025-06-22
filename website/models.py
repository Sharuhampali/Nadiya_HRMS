from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime, timedelta,date, time
import pytz
india_timezone = pytz.timezone('Asia/Kolkata')

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property

class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(512), nullable=False)
    earned =  db.Column(db.Float, default=0)
    medic = db.Column(db.Float, default=0)
    pay =  db.Column(db.Float, default=0)
    role = db.Column(db.String(150))
    probation = db.Column(db.Boolean, default = 0)
    photo = db.Column(db.String(150))
    documents = db.relationship('Document', backref='user', lazy=True)
    reset_token = db.Column(db.String(36), nullable=True)

    attendances = db.relationship('Attendance', backref='user', lazy=True)

    def set_probation_status(self, is_probation):
        """Update probation status and reset leave balances if on probation."""
        self.probation = is_probation
        if is_probation:
            self.earned = 15
            self.medic = 6
        db.session.commit()
    
    @hybrid_property 
    def total_compoff(self):
        return sum(attendance.compoff for attendance in self.attendances)
    
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    latitude = db.Column(db.String(50))
    longitude = db.Column(db.String(50))
    entry_time = db.Column(db.Time)  # Store only time
    exit_time = db.Column(db.Time)  # Store only time
    entry_location = db.Column(db.String(255))  # Store address for entry
    exit_location = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    compoff = db.Column(db.Float, default=0)
    hol = db.Column(db.Float, default=0)
    date = db.Column(db.Date)
    day = db.Column(db.String(150))
    totes = db.Column(db.Integer, default=0)
    reason = db.Column(db.Text)
    site_name = db.Column(db.String(150), nullable=True)  # New field for site/customer name


    def total_time_worked(self):
        if self.entry_time and self.exit_time:
            entry_time_dt = datetime.combine(date.today(), self.entry_time)
            exit_time_dt = datetime.combine(date.today(), self.exit_time)
            if exit_time_dt < entry_time_dt:
                exit_time_dt += timedelta(days=1)
            return exit_time_dt - entry_time_dt
        return None

    def extra_time_worked(self):
        total_time = self.total_time_worked()
        if total_time:
            if self.hol == 10000:
                return total_time
            return total_time - timedelta(hours=8.5)
        return None

    def calculate_comp_off(self):
        extra_time = self.extra_time_worked()
        if extra_time and extra_time.total_seconds() > 0:
            extra_hours = extra_time.total_seconds() / 3600
            if extra_hours >= 8.5:
                self.compoff = 1
            elif extra_hours >= 4:
                self.compoff = 0.5
        return self.compoff

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days =  db.Column(db.Float)
    approved = db.Column(db.Boolean, default=False)
    rejected = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.String(150))
    reason = db.Column(db.Text)
    ltype = db.Column(db.String(150))
    leaves_data = db.Column(db.String(150))  # JSON string to store leave data
    
    user = db.relationship('User', backref='leaves', lazy=True)

class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    date = db.Column(db.Date, nullable=False)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# class Upload(db.Model):
#     __tablename__ = 'uploads'
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     filename = db.Column(db.String(255), nullable=False)
#     bucket_name = db.Column(db.String(50), nullable=False)  # 'photos' or 'docs'
#     file_path = db.Column(db.String(512), nullable=False)
#     uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
