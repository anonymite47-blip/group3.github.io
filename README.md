# Web-Based Student Attendance Monitoring and Management System
Santa Cruz Institute — Computer Science Department

## Stack
Flask + Flask-SQLAlchemy + Flask-Login. Uses SQLite by default (zero setup)
and can be pointed at MySQL for deployment (e.g. PythonAnywhere).

## Setup

```bash
Run CMD as admin.
Type cd/[file directory]/attendance_app
py -m venv venv
type venv\Scripts\activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

py seed.py                  # creates the database + sample data
py run.py                   # starts the dev server at http://127.0.0.1:5000
```

## Once installed, use these codes:

```bash
1. Run CMD as admin.
2. Type cd/[file directory]/attendance_app
3. type py -m venv venv after step 2.
4. type venv\Scripts\activate.
5. type py seed.py. Wait until CMD successfully executes.
6. type py run.py. Must have an internet connection in order to proceed!
7. Copy http://127.0.0.1:5000 then paste it in on your browser.
```

## Sample logins (created by seed.py)

| Role    | Email                        | Password    |
|---------|-------------------------------|-------------|
| Faculty | a.delacruz@sci.edu.ph        | password123 |
| Student | andrea.delmundo@sci.edu.ph   | password123 |

## Project structure

```
attendance_app/
├── app/
│   ├── __init__.py       # app factory
│   ├── models.py         # User, Section, AttendanceRecord
│   ├── auth.py           # login / logout routes
│   ├── main.py           # dashboard, reports, students, settings, student view
│   ├── static/style.css  # shared stylesheet (matches the mockup design system)
│   └── templates/        # base.html + one template per screen
├── config.py
├── run.py
├── seed.py                # creates tables + sample data
└── requirements.txt
```

## Pages implemented (matches the six mockup screens)

1. **Login** — `/login`, role determined automatically from the account
2. **Faculty Dashboard** — `/dashboard`, mark Present/Late/Absent/Excused per student, live counts
3. **Reports** — `/reports`, weekly attendance rate + record list per section
4. **Students** — `/students`, searchable roster
5. **Settings** — `/settings`, notification toggles (SMS/Email/In-app)
6. **Student View** — `/my-attendance`, today's status + attendance-rate ring + history

## Switching to MySQL (for PythonAnywhere deployment)

Set the `DATABASE_URL` environment variable before running:

```bash
export DATABASE_URL="mysql+pymysql://username:password@hostname/databasename"
python seed.py
python run.py
```

## Not yet built (next steps)
- Add Student form (Students page currently list/search only)
- SMS/Email sending (toggles save the preference; actual sending needs an
  SMS gateway / email service, which requires internet access per our
  earlier hosting discussion)
- Export CSV button on Reports
- Password reset flow
