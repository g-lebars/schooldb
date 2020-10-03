from flask import request
from app import babel
from flask_babelex import gettext, lazy_gettext
from flask_user import current_user


language_choices = [('fr', lazy_gettext(u'French')), 
                    ('en', lazy_gettext(u'English')),
                    ('de', lazy_gettext(u'German')),
                    ]

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    if not current_user.is_anonymous:
        print("Current language: ",current_user.locale)
        return 'fr'
    # otherwise try to guess the language from the user accept
    # header the browser transmits.  We support de/fr/en in this
    # example.  The best match wins.
    lang=request.accept_languages.best_match(['fr','de','en'])
    return lang


@babel.timezoneselector
def get_timezone():
    return 'UTC'