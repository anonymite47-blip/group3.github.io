import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Change this before deploying — never keep a default secret key in production.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-this')

    # Defaults to a local SQLite file so it runs with zero setup.
    # For PythonAnywhere / MySQL, set DATABASE_URL to something like:
    #   mysql+pymysql://username:password@hostname/databasename
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'attendance.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
