from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_babelex import Babel
from config import Config
from flask_migrate import Migrate


app = Flask(__name__)
app.config.from_object(Config)

babel = Babel(app)
# Patching flask-babelex

Bootstrap(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from auth import User, CustomUserManager
user_manager = CustomUserManager(app,db,User)

import auth
app.register_blueprint(auth.bp)

import books
app.register_blueprint(books.bp)
app.add_url_rule('/', endpoint='books.index')

from navbar import nav
nav.init_app(app)

db.create_all()

from auth import Role
# Create 'member@example.com' user with no roles
if not User.query.filter(User.username == 'user').first():
        user = User(
            username='user',
            password=user_manager.hash_password('Password1'),
        )
        db.session.add(user)
        db.session.commit()

    # Create 'admin@example.com' user with 'Admin' and 'Agent' roles
if not User.query.filter(User.username == 'admin').first():
        user = User(
            username = 'admin',
            password=user_manager.hash_password('Password1'),
        )
        user.roles.append(Role(name='Admin'))
        user.roles.append(Role(name='Agent'))
        db.session.add(user)
        db.session.commit()

