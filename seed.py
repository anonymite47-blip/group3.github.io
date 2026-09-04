"""
Run this once to create the database tables and load sample data:
    python seed.py

Sample logins after seeding:
    Faculty:  a.delacruz@sci.edu.ph / password123
    Student:  andrea.delmundo@sci.edu.ph / password123
"""
from datetime import date, timedelta, datetime
from app import create_app, db
from app.models import User, Section, AttendanceRecord

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    # Faculty / adviser
    prof = User(full_name='Alexandra Dela Cruz', email='a.delacruz@sci.edu.ph', role='faculty')
    prof.set_password('password123')
    db.session.add(prof)
    db.session.commit()

    # Section
    section = Section(name='BSCS 3A', subject='Data Structures', adviser_id=prof.id)
    db.session.add(section)
    db.session.commit()

    # Students
    student_names = [
        ('Andrea Del Mundo', 'andrea.delmundo@sci.edu.ph', '2023-00114'),
        ('James Matthew Maac', 'james.maac@sci.edu.ph', '2023-00127'),
        ('Marc Nelson Jimenez', 'marc.jimenez@sci.edu.ph', '2023-00133'),
        ('Bea Fernandez', 'bea.fernandez@sci.edu.ph', '2023-00152'),
        ('Kyla Reyes', 'kyla.reyes@sci.edu.ph', '2023-00163'),
    ]

    students = []
    for name, email, no in student_names:
        u = User(full_name=name, email=email, role='student', student_no=no, section_id=section.id)
        u.set_password('password123')
        db.session.add(u)
        students.append(u)
    db.session.commit()

    # A few days of sample attendance so Dashboard/Reports/Student View aren't empty
    statuses_cycle = ['present', 'present', 'late', 'present', 'absent']
    for day_offset in range(5, -1, -1):
        d = date.today() - timedelta(days=day_offset)
        for i, s in enumerate(students):
            status = statuses_cycle[(i + day_offset) % len(statuses_cycle)]
            rec = AttendanceRecord(
                student_id=s.id,
                section_id=section.id,
                date=d,
                status=status,
                time_marked=None if status == 'absent' else datetime.combine(d, datetime.min.time()).replace(hour=7, minute=55)
            )
            db.session.add(rec)
    db.session.commit()

    print('Database seeded.')
    print('Faculty login:  a.delacruz@sci.edu.ph / password123')
    print('Student login:  andrea.delmundo@sci.edu.ph / password123')
