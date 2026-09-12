from datetime import date, datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import User, Section, AttendanceRecord

main_bp = Blueprint('main', __name__)


def faculty_required(view):
    """Blocks students from faculty-only pages (Dashboard, Reports, Students)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user.role not in ('faculty', 'admin'):
            return redirect(url_for('main.student_view'))
        return view(*args, **kwargs)
    return wrapped


@main_bp.route('/')
@login_required
def index():
    if current_user.role == 'student':
        return redirect(url_for('main.student_view'))
    return redirect(url_for('main.dashboard'))


# ---------- FACULTY / ADMIN ----------

@main_bp.route('/dashboard')
@login_required
@faculty_required
def dashboard():
    sections = Section.query.filter_by(adviser_id=current_user.id).all()
    section_id = request.args.get('section_id', type=int)
    section = Section.query.get(section_id) if section_id else (sections[0] if sections else None)

    roster = []
    counts = {'present': 0, 'late': 0, 'absent': 0, 'excused': 0}

    if section:
        today = date.today()
        students = User.query.filter_by(role='student', section_id=section.id).all()
        for s in students:
            rec = AttendanceRecord.query.filter_by(
                student_id=s.id, section_id=section.id, date=today
            ).first()
            status = rec.status if rec else None
            if status in counts:
                counts[status] += 1
            roster.append({
                'student': s,
                'status': status,
                'time': rec.time_marked if rec else None,
            })

    return render_template(
        'dashboard.html', sections=sections, section=section,
        roster=roster, counts=counts, total=len(roster)
    )


@main_bp.route('/attendance/mark', methods=['POST'])
@login_required
@faculty_required
def mark_attendance():
    student_id = request.form.get('student_id', type=int)
    section_id = request.form.get('section_id', type=int)
    status = request.form.get('status')
    today = date.today()

    rec = AttendanceRecord.query.filter_by(
        student_id=student_id, section_id=section_id, date=today
    ).first()
    if not rec:
        rec = AttendanceRecord(student_id=student_id, section_id=section_id, date=today)
        db.session.add(rec)

    rec.status = status
    rec.time_marked = None if status == 'absent' else datetime.now()
    db.session.commit()

    return redirect(url_for('main.dashboard', section_id=section_id))


@main_bp.route('/reports')
@login_required
@faculty_required
def reports():
    sections = Section.query.filter_by(adviser_id=current_user.id).all()
    section_id = request.args.get('section_id', type=int)
    section = Section.query.get(section_id) if section_id else (sections[0] if sections else None)

    records = []
    if section:
        records = (AttendanceRecord.query
                   .filter_by(section_id=section.id)
                   .order_by(AttendanceRecord.date.desc())
                   .limit(50)
                   .all())

    total = len(records)
    present = len([r for r in records if r.status == 'present'])
    late = len([r for r in records if r.status == 'late'])
    absent = len([r for r in records if r.status == 'absent'])
    rate = round((present + late) / total * 100) if total else 0

    return render_template(
        'reports.html', sections=sections, section=section, records=records,
        present=present, late=late, absent=absent, rate=rate
    )


@main_bp.route('/students')
@login_required
@faculty_required
def students():
    q = request.args.get('q', '').strip()
    query = User.query.filter_by(role='student')
    if q:
        query = query.filter(User.full_name.ilike(f'%{q}%'))
    student_list = query.order_by(User.full_name).all()
    return render_template('students.html', students=student_list, q=q)


# ---------- STUDENT ----------

@main_bp.route('/my-attendance')
@login_required
def student_view():
    records = (AttendanceRecord.query
               .filter_by(student_id=current_user.id)
               .order_by(AttendanceRecord.date.desc())
               .limit(20)
               .all())

    total = len(records)
    present_like = len([r for r in records if r.status in ('present', 'late')])
    rate = round(present_like / total * 100) if total else 0

    today_rec = AttendanceRecord.query.filter_by(
        student_id=current_user.id, date=date.today()
    ).first()
    today_status = today_rec.status if today_rec else 'not marked'

    return render_template(
        'student_view.html', records=records, rate=rate, today_status=today_status
    )


# ---------- SHARED ----------

@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.sms_notify = 'sms_notify' in request.form
        current_user.email_notify = 'email_notify' in request.form
        current_user.inapp_notify = 'inapp_notify' in request.form
        db.session.commit()
        return redirect(url_for('main.settings'))
    return render_template('settings.html')
