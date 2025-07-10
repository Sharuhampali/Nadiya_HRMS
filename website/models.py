from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime, timedelta, date, time
import pytz
from sqlalchemy.ext.hybrid import hybrid_property

india_timezone = pytz.timezone('Asia/Kolkata')


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150))
    nad_id = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(512), nullable=False)
    earned = db.Column(db.Float, default=0)
    medic = db.Column(db.Float, default=0)
    pay = db.Column(db.Float, default=0)
    role = db.Column(db.String(150))
    probation = db.Column(db.Boolean, default=0)
    photo = db.Column(db.String(150))
    reset_token = db.Column(db.String(36), nullable=True)

    documents = db.relationship('Document', backref='user', lazy=True)
    attendances = db.relationship('Attendance', backref='user', lazy=True)
    compoff_requests = db.relationship('CompOffRequest', backref='user', lazy=True)
    joining_date = db.Column(db.DateTime, default=datetime.utcnow)

    def set_probation_status(self, is_probation):
        self.probation = is_probation
        if is_probation:
            self.earned = 15
            self.medic = 6
        db.session.commit()

    @hybrid_property
    def total_compoff(self):
        return sum(r.value for r in self.compoff_requests if r.status == 'approved' and not r.used)


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
    entry_time = db.Column(db.Time)
    exit_time = db.Column(db.Time)
    entry_location = db.Column(db.String(255))
    exit_location = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date)
    day = db.Column(db.String(150))
    totes = db.Column(db.Integer, default=0)
    reason = db.Column(db.Text)
    site_name = db.Column(db.String(150), nullable=True)
    site_name_e = db.Column(db.String(150), nullable=True)
    hol = db.Column(db.Float, default=0)
    exit_report_submitted = db.Column(db.Boolean, default=False)

    def total_time_worked(self):
        if self.entry_time and self.exit_time and self.date:
            entry_dt = datetime.combine(self.date, self.entry_time)
            exit_dt = datetime.combine(
                self.date if self.exit_time >= self.entry_time else self.date + timedelta(days=1),
                self.exit_time
            )
            return exit_dt - entry_dt
        return None

    def extra_time_worked(self):
        total_time = self.total_time_worked()
        if not total_time:
            return None

        if self.hol == 10000:
            return total_time

        expected_hours = timedelta(hours=8.5)
        try:
            user = User.query.get(self.user_id)
            if user and user.email == "support@nadiya.in":
                expected_hours = timedelta(hours=6.5)
        except:
            pass

        return total_time - expected_hours

    def calculate_comp_off(self):
        from .models import CompOffRequest  # avoid circular import
        extra_time = self.extra_time_worked()
        if not extra_time or extra_time.total_seconds() <= 0:
            return None

        hours = extra_time.total_seconds() / 3600
        user = User.query.get(self.user_id)
        value = 0

        if user and user.email == "support@nadiya.in":
            if hours >= 6.5:
                value = 1.0
            elif hours >= 3:
                value = 0.5
        else:
            if hours >= 8.5:
                value = 1.0
            elif hours >= 4:
                value = 0.5

        if value > 0:
            existing = CompOffRequest.query.filter_by(attendance_id=self.id).first()
            if not existing:
                request = CompOffRequest(
                    user_id=self.user_id,
                    attendance_id=self.id,
                    value=value,
                    status='pending'
                )
                db.session.add(request)
            elif existing.status == 'pending':
                existing.value = value
            db.session.commit()
        return value


class CompOffRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=False)

    value = db.Column(db.Float, nullable=False)  # 0.5 or 1.0
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    approved_by = db.Column(db.String(150), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    used = db.Column(db.Boolean, default=False)
    requested_on = db.Column(db.DateTime, default=datetime.utcnow)

    attendance = db.relationship('Attendance', backref='compoff_request')


class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days = db.Column(db.Float)
    approved = db.Column(db.Boolean, default=False)
    rejected = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.String(150))
    reason = db.Column(db.Text)
    ltype = db.Column(db.String(150))
    leaves_data = db.Column(db.String(150))
    user = db.relationship('User', backref='leaves', lazy=True)


class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    date = db.Column(db.Date, nullable=False)


announcement_user = db.Table(
    'announcement_user',
    db.Column('announcement_id', db.Integer, db.ForeignKey('announcement.id', ondelete='CASCADE')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image_url = db.Column(db.String(300))
    doc_url = db.Column(db.String(300))
    recipients = db.relationship(
        'User',
        secondary=announcement_user,
        backref=db.backref('announcements_received', lazy='dynamic'),
        passive_deletes=True,
        lazy='dynamic'
    )


class AnnouncementAcknowledgment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'))
    acknowledged_on = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='acknowledgments')
    announcement = db.relationship('Announcement', backref='acknowledgments')


class IntermediateLog(db.Model):
    __tablename__ = 'intermediate_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    entry_type = db.Column(db.String(10))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    location = db.Column(db.String(255))
    site = db.Column(db.String(150), nullable=True)
    user = db.relationship('User', backref='intermediate_logs')


class EditRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_by = db.Column(db.String(120), nullable=False)
    entry_time = db.Column(db.Time, nullable=True)
    exit_time = db.Column(db.Time, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    token = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='edit_requests')


class ExitReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=False)
    site_name = db.Column(db.String(100), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    activities_completed = db.Column(db.Text, nullable=False)
    tomorrow_plan = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='exit_reports')
    attendance = db.relationship('Attendance', backref='exit_report')
