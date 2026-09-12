"""
Adds the real 1st Semester subjects for BSCS 1-4 as Section rows,
one row per (year level, subject) combination.

Safe to run more than once, and safe to run on a database that already
has real students/attendance — it does NOT wipe anything. It only
skips subjects that already exist and adds the ones that don't.

Usage:
    python seed_subjects.py

Adjust SCHOOL_YEAR below if this isn't for 2026-2027.
"""
from app import create_app, db
from app.models import Section

SCHOOL_YEAR = '2026-2027'
SEMESTER = '1st Semester'

CURRICULUM = {
    'BSCS 1': [
        'Computer Programming 1',
        'Fundamentals of Programming',
        'Intermediate Programming',
        'Introduction to Computing',
        'Mathematics in the Modern World',
        'Physical Education 1',
        'The Contemporary World',
        'Understanding the Self',
    ],
    'BSCS 2': [
        'Application Development and Emerging Tech',
        'Computer Programming 3',
        'Data Structures and Algorithms',
        'Discrete Structure 2',
        'Istruktura ng Wikang Filipino',
        'PathFit 1 / PathFit 3',
        'Philippine History',
        'Principles of Communication',
        'The Entrepreneurial Mind',
    ],
    'BSCS 3': [
        'Automata Theory and Formal Language',
        'Computer Graphics and Visual Computing',
        'Human Computer Interaction',
        'Information Assurance and Society',
        'Methods of Research',
        'Object-Oriented Programming',
        'Philippine Literature',
        'Research',
        'Technical Writing',
    ],
    'BSCS 4': [
        'Artificial Intelligence',
        'Computer Aided Design',
        'Intro to Economics w/ Tax Land Reform',
        'Life in the IT Era',
        'Philippine Government and New Constitution',
        'Thesis 1',
    ],
}

app = create_app()

with app.app_context():
    added = 0
    skipped = 0

    for year_level, subjects in CURRICULUM.items():
        for subject in subjects:
            exists = Section.query.filter_by(
                name=year_level, subject=subject,
                school_year=SCHOOL_YEAR, semester=SEMESTER
            ).first()

            if exists:
                skipped += 1
                continue

            db.session.add(Section(
                name=year_level, subject=subject,
                school_year=SCHOOL_YEAR, semester=SEMESTER,
                adviser_id=None  # assign later via the Sections page
            ))
            added += 1

    db.session.commit()
    print(f'Added {added} new section/subject rows, skipped {skipped} that already existed.')
    print('Adviser is unassigned for all of them — set that per subject on the Sections page.')
