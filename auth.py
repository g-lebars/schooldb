from app import db
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.urls import url_parse
import functools
from flask import (
        Blueprint, flash, g, redirect, render_template, request, session, url_for
        )
from flask_wtf import FlaskForm
from wtforms import TextField, StringField, PasswordField, BooleanField, validators, SubmitField, SelectField
from wtforms.validators import *
from flask_table import Table, BoolCol, Col, ButtonCol 
from languages import language_choices
from flask_babelex import gettext, lazy_gettext
from flask_babelex import refresh as babrefresh

from sqlalchemy_utils import UUIDType
import uuid
from flask_user import UserManager, UserMixin, current_user, login_required, roles_required


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(UUIDType, primary_key = True, default=uuid.uuid4, nullable=False)
    username = db.Column(db.String(80), unique = True, nullable = False )
    password = db.Column(db.String, nullable = False)
    locale = db.Column(db.String, default= 'fr', nullable = False)
    active = db.Column('is_active', db.Boolean, nullable=False, default=True)
    first_name = db.Column(db.String(50), nullable=False, default='')
    last_name = db.Column(db.String(50), nullable=False, default='')

     # Define the relationship to Role via UserRoles
    roles = db.relationship('Role', secondary='user_roles')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(50), unique = True)
    description = db.Column(db.String(180))

class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))



bp = Blueprint('auth', __name__, url_prefix='/auth')


class UUIDLoginForm(FlaskForm):
    UUID = TextField('UUID',[validators.DataRequired()])
    remember_me = BooleanField(lazy_gettext(u'Remember me'))
    submit = SubmitField(lazy_gettext(u'Login'))

class CustomUserManager(UserManager):
    def login_view(self):
        """Prepare and process the login form."""

        # Authenticate username/email and login authenticated users.

        safe_next_url = self._get_safe_next_url('next', self.USER_AFTER_LOGIN_ENDPOINT)
        safe_reg_next = self._get_safe_next_url('reg_next', self.USER_AFTER_REGISTER_ENDPOINT)

        # Immediately redirect already logged in users
        if self.call_or_get(current_user.is_authenticated) and self.USER_AUTO_LOGIN_AT_LOGIN:
            return redirect(safe_next_url)

        # Initialize form
        login_form = self.LoginFormClass(request.form)  # for login.html
        uuidlogin_form = UUIDLoginForm()
        register_form = self.RegisterFormClass()  # for login_or_register.html
        if request.method != 'POST':
            login_form.next.data = register_form.next.data = safe_next_url
            login_form.reg_next.data = register_form.reg_next.data = safe_reg_next

        # Process valid POST
        if request.method == 'POST' and login_form.validate():
            # Retrieve User
            user = None
            user_email = None
            if self.USER_ENABLE_USERNAME:
                # Find user record by username
                user = self.db_manager.find_user_by_username(login_form.username.data)

                # Find user record by email (with form.username)
                if not user and self.USER_ENABLE_EMAIL:
                    user, user_email = self.db_manager.get_user_and_user_email_by_email(login_form.username.data)
            else:
                # Find user by email (with form.email)
                user, user_email = self.db_manager.get_user_and_user_email_by_email(login_form.email.data)

            if user:
                # Log user in
                safe_next_url = self.make_safe_url(login_form.next.data)
                return self._do_login_user(user, safe_next_url, login_form.remember_me.data)
        elif request.method == 'POST' and uuidlogin_form.validate():
            # Retrieve User
            user = None
            user_email = None
            
            user = self.db_manager.get_user_by_id(uuidlogin_form.UUID.data)

            if user:
                # Log user in
                safe_next_url = self.make_safe_url(login_form.next.data)
                return self._do_login_user(user, safe_next_url, uuidlogin_form.remember_me.data)

        # Render form
        self.prepare_domain_translations()
        template_filename = self.USER_LOGIN_AUTH0_TEMPLATE if self.USER_ENABLE_AUTH0 else self.USER_LOGIN_TEMPLATE
        return render_template(template_filename,
                      form=login_form,
                      login_form=login_form,
                      uuidlogin_form=uuidlogin_form,
                      register_form=register_form)



class UserEditForm(FlaskForm):
    password = PasswordField(lazy_gettext(u'Password'),[validators.InputRequired()])
    admin = BooleanField(lazy_gettext(u'Administrator'))
    Submit = SubmitField(lazy_gettext(u'Save'))



class UserSelfEditForm(FlaskForm):
    old_password = PasswordField(lazy_gettext(u'Old password'),[validators.Optional()])
    new_password = PasswordField(lazy_gettext(u'New password'),[EqualTo('confirm_password', message=lazy_gettext(u'Passwords must match'))])
    confirm_password = PasswordField(lazy_gettext(u'Repeat password'))
    language = SelectField(lazy_gettext(u'Language'),choices=language_choices)
    submit = SubmitField(lazy_gettext(u'Save'))



@bp.route('/register', methods=('GET','POST'))
@roles_required('Admin')
def register():

    form = UserCreationForm()

    if form.validate_on_submit():
        qry = db.session.query(User).filter(
                    User.username == form.username.data)
        if qry.first() is not None:
            flash(lazy_gettext(u'User {} is already registered.').format(form.username.data),'danger')

        user = User(form.username.data, form.password.data, form.admin.data)
        user.locale = form.language.data
        db.session.add(user)
        db.session.commit()
      
        return redirect(url_for('index'))

    return render_template('auth/register.html', form=form)


@bp.route('/init', methods=('GET','POST'))
def auth_init():
    qry = db.session.query(User)
    if qry.first() is not None:
        flash(lazy_gettext(u'An admin user has already been created'),'danger')
        return redirect(url_for('index'))

    form = UserCreationForm()

    if form.validate_on_submit():
        user = User(form.username.data, form.password.data, True)
        user.locale = form.language.data
        db.session.add(user)
        db.session.commit()
      
        return redirect(url_for('index'))

    return render_template('auth/register.html', form=form)


class LanguageCol(Col):
    def td_format(self,content):
        values = dict(language_choices)
        if values[content] is not None:
            return values[content]
        else: 
            return lazy_gettext(u'Unknown Language')


class RoleCol(Col):
    def td_format(self,content):
        roles=[]
        for role in content:
            roles+=role.name +', '
        return roles[:-2]


class UserTable(Table):
    classes = ['table']
    id = Col('Id')
    username = Col(lazy_gettext(u'Username'))
    roles = RoleCol(lazy_gettext(u'Roles'))
    locale = LanguageCol(lazy_gettext(u'Language'))
    edit = ButtonCol(lazy_gettext(u'Edit'), '.edit', url_kwargs=dict(userid='id'))


@bp.route('/userlist')
@roles_required('Admin')
def userlist():
    results = User.query.all()
 
    if not results:
        flash(lazy_gettext(u'No users found!'))
        return redirect('/')
    else:
        # display results
        table = UserTable(results, no_items='There is nothing')
        table.__html__()
        table.border = True
        return render_template('auth/userlist.html', table=table)

@bp.route('/user/<uuid:userid>', methods=['GET', 'POST'])
@login_required
def edit(userid):

    qry = db.session.query(User).filter(User.id==userid)
    user = qry.first()

    if user:
        if user.username == current_user.username:
            form = UserSelfEditForm()

            if form.validate_on_submit():
                # Save modifications
                if form.new_password.data is not '' and check_password_hash(user.password, form.old_password.data):
                    user.password = generate_password_hash(form.new_password.data)
                elif form.new_password.data is not '':
                    flash(lazy_gettext(u'Incorrect old password'))

                user.locale = form.language.data
                print(current_user.locale)# = form.language.data
                db.session.commit()
                babrefresh()
                flash(lazy_gettext(u'User \"{}\" updated successfully!').format(user.username))
                return redirect(url_for('books.index'))
                

            return render_template('auth/edit.html', form=form, username=user.username)

        elif current_user.has_roles('Admin'):
            form = UserEditForm()

            if form.validate_on_submit():
                # Save modifications
                user.password = generate_password_hash(form.password.data)
                user.admin = form.admin.data
                db.session.commit()
                flash(lazy_gettext(u'User updated successfully!'))
                return redirect(url_for('.userlist'))

            return render_template('auth/edit.html', form=form, username=user.username)

        else:
            flash(lazy_gettext(u"You don't have the rights to edit user: \"{username}\"").format(username=userid.hex))
            redirect(url_for('.userlist'))

    else:
        flash(lazy_gettext(u'ERROR: User \"{username}\" doesn''t exist').format(username=userid.hex))
        return redirect(url_for('.userlist'))


@bp.route('/user/<uuid:userid>/barcode', methods=['GET', 'POST'])
@login_required
def barcode(userid):
    import barcode
    from barcode import writer
    from io import BytesIO, StringIO

    qry = db.session.query(User).filter(User.id==userid)
    user = qry.first()

    if user:
        if userid == current_user.id:
            fp = BytesIO()
            print(userid)
            code128 = barcode.get_barcode_class('code128')
            the_code = code128(userid.hex)
            the_code.write(fp)
            encoded_output = fp.getvalue().decode()
            encoded_output = encoded_output[encoded_output.find('<svg'):]
            fp.close()
            return render_template('auth/barcode.html', encoded_output=encoded_output, username=current_user.username)

        else:
            flash(lazy_gettext(u"You don't have the rights to display: \"{user}\"'s barcode").format(user=userid.hex))
            redirect(url_for('index'))
    else:
        flash(lazy_gettext(u'ERROR: User \"{userid}\" doesn''t exist').format(userid=userid.hex))
        return redirect(url_for('index'))
