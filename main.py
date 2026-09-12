import csv
import io
from datetime import date, datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, abort, Response
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


@main_bp.route('/reports/export')
@login_required
@faculty_required
def export_reports():
    sections = Section.query.filter_by(adviser_id=current_user.id).all()
    section_id = request.args.get('section_id', type=int)
    section = Section.query.get(section_id) if section_id else (sections[0] if sections else None)

    records = []
    if section:
        records = (AttendanceRecord.query
                   .filter_by(section_id=section.id)
                   .order_by(AttendanceRecord.date.desc())
                   .all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Student Name', 'Student No.', 'Status'])
    for r in records:
        writer.writerow([
            r.date.strftime('%Y-%m-%d'),
            r.student.full_name,
            r.student.student_no,
            r.status.capitalize(),
        ])

    section_label = section.name.replace(' ', '_') if section else 'report'
    filename = f'attendance_{section_label}_{date.today().isoformat()}.csv'

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
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


@main_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_student():
    sections = Section.query.all()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        student_no = request.form.get('student_no', '').strip()
        section_id = request.form.get('section_id', type=int)
        password = request.form.get('password', '').strip()

        error = None
        if not full_name or not email or not student_no or not password:
            error = 'All fields are required.'
        elif User.query.filter_by(email=email).first():
            error = 'That email is already registered.'
        elif User.query.filter_by(student_no=student_no).first():
            error = 'That student number is already registered.'

        if error:
            return render_template('add_student.html', sections=sections, error=error, form=request.form)

        student = User(
            full_name=full_name, email=email, student_no=student_no,
            role='student', section_id=section_id or None
        )
        student.set_password(password)
        db.session.add(student)
        db.session.commit()
        return redirect(url_for('main.students'))

    return render_template('add_student.html', sections=sections, error=None, form={})


@main_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
@faculty_required
def edit_student(student_id):
    student = User.query.filter_by(id=student_id, role='student').first()
    if not student:
        abort(404)
    sections = Section.query.all()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        student_no = request.form.get('student_no', '').strip()
        section_id = request.form.get('section_id', type=int)
        new_password = request.form.get('password', '').strip()

        error = None
        if not full_name or not email or not student_no:
            error = 'Name, email, and student number are required.'
        elif User.query.filter(User.email == email, User.id != student.id).first():
            error = 'That email is already registered to another account.'
        elif User.query.filter(User.student_no == student_no, User.id != student.id).first():
            error = 'That student number is already registered to another account.'

        if error:
            return render_template(
                'edit_student.html', student=student, sections=sections,
                error=error, form=request.form
            )

        student.full_name = full_name
        student.email = email
        student.student_no = student_no
        student.section_id = section_id or None
        if new_password:
            student.set_password(new_password)
        db.session.commit()
        return redirect(url_for('main.students'))

    return render_template('edit_student.html', student=student, sections=sections, error=None, form=None)


@main_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@faculty_required
def delete_student(student_id):
    student = User.query.filter_by(id=student_id, role='student').first()
    if not student:
        abort(404)
    AttendanceRecord.query.filter_by(student_id=student.id).delete()
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('main.students'))


# ---------- SECTIONS ----------

@main_bp.route('/sections')
@login_required
@faculty_required
def sections():
    section_list = Section.query.order_by(Section.school_year.desc(), Section.name).all()
    return render_template('sections.html', sections=section_list)


@main_bp.route('/sections/add', methods=['GET', 'POST'])
@login_required
@faculty_required
def add_section():
    advisers = User.query.filter(User.role.in_(['faculty', 'admin'])).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subject = request.form.get('subject', '').strip()
        school_year = request.form.get('school_year', '').strip()
        semester = request.form.get('semester', '').strip()
        adviser_id = request.form.get('adviser_id', type=int)

        error = None
        if not name or not subject:
            error = 'Section name and subject are required.'

        if error:
            return render_template('add_section.html', advisers=advisers, error=error, form=request.form)

        section = Section(
            name=name, subject=subject,
            school_year=school_year or None, semester=semester or None,
            adviser_id=adviser_id or None
        )
        db.session.add(section)
        db.session.commit()
        return redirect(url_for('main.sections'))

    return render_template('add_section.html', advisers=advisers, error=None, form={})


@main_bp.route('/sections/<int:section_id>/edit', methods=['GET', 'POST'])
@login_required
@faculty_required
def edit_section(section_id):
    section = Section.query.get(section_id)
    if not section:
        abort(404)
    advisers = User.query.filter(User.role.in_(['faculty', 'admin'])).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subject = request.form.get('subject', '').strip()
        school_year = request.form.get('school_year', '').strip()
        semester = request.form.get('semester', '').strip()
        adviser_id = request.form.get('adviser_id', type=int)

        error = None
        if not name or not subject:
            error = 'Section name and subject are required.'

        if error:
            return render_template(
                'edit_section.html', section=section, advisers=advisers,
                error=error, form=request.form
            )

        section.name = name
        section.subject = subject
        section.school_year = school_year or None
        section.semester = semester or None
        section.adviser_id = adviser_id or None
        db.session.commit()
        return redirect(url_for('main.sections'))

    return render_template('edit_section.html', section=section, advisers=advisers, error=None, form=None)


@main_bp.route('/sections/<int:section_id>/delete', methods=['POST'])
@login_required
@faculty_required
def delete_section(section_id):
    section = Section.query.get(section_id)
    if not section:
        abort(404)
    # Unassign students rather than deleting them
    for student in User.query.filter_by(section_id=section.id).all():
        student.section_id = None
    AttendanceRecord.query.filter_by(section_id=section.id).delete()
    db.session.delete(section)
    db.session.commit()
    return redirect(url_for('main.sections'))


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
