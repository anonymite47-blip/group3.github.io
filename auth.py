import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db, oauth
from app.models import User, Section
from app.sms import generate_otp, send_sms, is_dev_mode

auth_bp = Blueprint('auth', __name__)

OTP_VALID_MINUTES = 10


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if user.role == 'student' and not user.phone_verified:
                _issue_otp(user)
                session['pending_verification_user_id'] = user.id
                flash('Please verify your mobile number to continue.')
                return redirect(url_for('auth.verify_phone'))

            login_user(user)
            return redirect(url_for('main.index'))

        flash('Invalid email or password.')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    sections = Section.query.order_by(Section.name).all()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        student_no = request.form.get('student_no', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '').strip()
        section_id = request.form.get('section_id', type=int)
        gender = request.form.get('gender', '').strip()
        year_level = request.form.get('year_level', '').strip()

        error = None
        if not all([full_name, email, student_no, phone_number, password]):
            error = 'All fields are required.'
        elif not (phone_number.isdigit() and len(phone_number) == 11 and phone_number.startswith('09')):
            error = 'Enter a valid PH mobile number, e.g. 09171234567.'
        elif User.query.filter_by(email=email).first():
            error = 'That email is already registered.'
        elif User.query.filter_by(student_no=student_no).first():
            error = 'That student number is already registered.'

        if error:
            return render_template('signup.html', sections=sections, error=error, form=request.form)

        student = User(
            full_name=full_name, email=email, student_no=student_no,
            phone_number=phone_number, role='student',
            section_id=section_id or None, phone_verified=False,
            gender=gender or None, year_level=year_level or None,
        )
        student.set_password(password)
        db.session.add(student)
        db.session.commit()

        _issue_otp(student)
        session['pending_verification_user_id'] = student.id
        return redirect(url_for('auth.verify_phone'))

    return render_template('signup.html', sections=sections, error=None, form={})


@auth_bp.route('/verify-phone', methods=['GET', 'POST'])
def verify_phone():
    user_id = session.get('pending_verification_user_id')
    if not user_id:
        return redirect(url_for('auth.signup'))

    student = User.query.get(user_id)
    if not student:
        session.pop('pending_verification_user_id', None)
        return redirect(url_for('auth.signup'))

    error = None

    if request.method == 'POST':
        if 'resend' in request.form:
            _issue_otp(student)
            error = 'A new code was sent.'
        else:
            code = request.form.get('code', '').strip()
            if not student.otp_code or not student.otp_expires_at or datetime.utcnow() > student.otp_expires_at:
                error = 'That code expired. Request a new one below.'
            elif code != student.otp_code:
                error = 'Incorrect code. Please try again.'
            else:
                student.phone_verified = True
                student.otp_code = None
                student.otp_expires_at = None
                db.session.commit()
                session.pop('pending_verification_user_id', None)
                login_user(student)
                return redirect(url_for('main.index'))

    return render_template(
        'verify_phone.html', student=student, error=error,
        dev_otp=(student.otp_code if is_dev_mode() else None)
    )


def _issue_otp(student):
    student.otp_code = generate_otp()
    student.otp_expires_at = datetime.utcnow() + timedelta(minutes=OTP_VALID_MINUTES)
    db.session.commit()
    send_sms(
        student.phone_number,
        f'Your Santa Cruz Institute Attendance System verification code is '
        f'{student.otp_code}. It expires in {OTP_VALID_MINUTES} minutes.'
    )


# ---------- GOOGLE SIGN-IN ----------

@auth_bp.route('/auth/google/login')
def google_login():
    if not current_app.config.get('GOOGLE_CLIENT_ID'):
        flash('Google Sign-In is not configured yet.')
        return redirect(url_for('auth.login'))
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/auth/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    userinfo = token.get('userinfo') or oauth.google.userinfo(token=token)
    email = userinfo['email'].strip().lower()
    name = userinfo.get('name') or email.split('@')[0]

    user = User.query.filter_by(email=email).first()

    if user:
        # Existing account (whether created via password signup or Google before) — just log in.
        if user.role == 'student' and not user.phone_verified:
            _issue_otp(user)
            session['pending_verification_user_id'] = user.id
            flash('Please verify your mobile number to continue.')
            return redirect(url_for('auth.verify_phone'))
        login_user(user)
        return redirect(url_for('main.index'))

    # No account yet — Google only gives us email + name, so we still need
    # student number and phone number before we can create one.
    session['google_pending_email'] = email
    session['google_pending_name'] = name
    return redirect(url_for('auth.complete_profile'))


@auth_bp.route('/complete-profile', methods=['GET', 'POST'])
def complete_profile():
    email = session.get('google_pending_email')
    name = session.get('google_pending_name')
    if not email:
        return redirect(url_for('auth.login'))

    sections = Section.query.order_by(Section.name).all()

    if request.method == 'POST':
        student_no = request.form.get('student_no', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        section_id = request.form.get('section_id', type=int)
        gender = request.form.get('gender', '').strip()
        year_level = request.form.get('year_level', '').strip()

        error = None
        if not student_no or not phone_number:
            error = 'Student number and mobile number are required.'
        elif not (phone_number.isdigit() and len(phone_number) == 11 and phone_number.startswith('09')):
            error = 'Enter a valid PH mobile number, e.g. 09171234567.'
        elif User.query.filter_by(student_no=student_no).first():
            error = 'That student number is already registered.'

        if error:
            return render_template(
                'complete_profile.html', email=email, name=name,
                sections=sections, error=error, form=request.form
            )

        student = User(
            full_name=name, email=email, student_no=student_no,
            phone_number=phone_number, role='student',
            section_id=section_id or None, phone_verified=False,
            gender=gender or None, year_level=year_level or None,
        )
        # Google-authenticated accounts don't use this password to sign in,
        # but the column is required, so set an unguessable random one.
        student.set_password(secrets.token_hex(16))
        db.session.add(student)
        db.session.commit()

        session.pop('google_pending_email', None)
        session.pop('google_pending_name', None)

        _issue_otp(student)
        session['pending_verification_user_id'] = student.id
        return redirect(url_for('auth.verify_phone'))

    return render_template(
        'complete_profile.html', email=email, name=name,
        sections=sections, error=None, form={}
    )
