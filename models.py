from datetime import date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    """Covers both faculty/admin accounts and student accounts.
    role is one of: 'admin', 'faculty', 'student'.
    student_no and section_id only apply when role == 'student'.
    """
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')

    student_no = db.Column(db.String(30), unique=True, nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=True)

    sms_notify = db.Column(db.Boolean, default=True)
    email_notify = db.Column(db.Boolean, default=True)
    inapp_notify = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)       # e.g. "BSCS 3A"
    subject = db.Column(db.String(100))                    # e.g. "Data Structures"
    adviser_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    adviser = db.relationship('User', foreign_keys=[adviser_id])
    students = db.relationship(
        'User', backref='section',
        foreign_keys=[User.section_id]
    )

    def __repr__(self):
        return f'<Section {self.name}>'


class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    status = db.Column(db.String(10), default='present')   # present, late, absent, excused
    time_marked = db.Column(db.DateTime, nullable=True)

    student = db.relationship('User', foreign_keys=[student_id])
    section = db.relationship('Section', foreign_keys=[section_id])

    __table_args__ = (
        db.UniqueConstraint('student_id', 'section_id', 'date', name='one_record_per_day'),
    )
