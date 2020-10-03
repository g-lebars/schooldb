import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    #Flask-User settings
    USER_ENABLE_USERNAME = True    # Enable username authentication
    USER_ENABLE_EMAIL = False      # Disable email authentication
    USER_APP_NAME = 'TMDB'

    #Babel settings
    BABEL_DEFAULT_LOCALE = 'fr'
    BABEL_DEFAULT_TIMEZONE = 'UTC'