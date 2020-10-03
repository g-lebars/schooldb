from app import db
from flask_wtf import FlaskForm
from wtforms import Form, TextField, SelectField, SubmitField, validators, ValidationError
from flask import (
        Blueprint, flash, g, redirect, render_template, request, url_for
        )
from werkzeug.exceptions import abort
from auth import login_required, User
from flask_table import Table, Col, LinkCol, ButtonCol, DatetimeCol
from flask_babelex import gettext, ngettext, lazy_gettext
from flask_user import current_user, login_required, roles_required

bp = Blueprint('games', __name__,  url_prefix='/games')

game_categories=[('game', lazy_gettext(u'Game'))
                ]

class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String, nullable = False )
    publisher = db.Column(db.String, nullable = False)
    isbn13 = db.Column(db.String(13), nullable = True)
    # renter information's:
    renter_name = db.Column(db.String, db.ForeignKey("users.username"), nullable =True)
    rented_time = db.Column(db.DateTime, nullable = True)
    renter = db.relationship("User", backref=db.backref("books", order_by = id), lazy = True)
    category = db.Column(db.String, nullable = False)


class SearchForm(FlaskForm):
    search = TextField('')
    submit = SubmitField(lazy_gettext(u'Search'))


def validate_isbn10(form, field):
    if field.data:
        if len(field.data) != 10:
            raise ValidationError(lazy_gettext(u'ISBN 10 must contain only numeric characters'))
        if not field.data.isdigit():
            raise ValidationError(lazy_gettext(u'ISBN 10 must contain only numeric characters'))

def validate_isbn13(form, field):
    if field.data:
        if len(field.data) != 13:
            raise ValidationError(lazy_gettext(u'ISBN 13 must be 10 character long'))
        if not field.data.isdigit():
            raise ValidationError(lazy_gettext(u'ISBN 13 must contain only numeric characters'))

class GameForm(FlaskForm):
    title = TextField(lazy_gettext(u'Title'),[validators.InputRequired()])
    publisher = TextField(lazy_gettext(u'Publisher'),[validators.InputRequired()])
    author = TextField(lazy_gettext(u'Author'))
    isbn10 = TextField('ISBN 10',[validate_isbn10])
    isbn13 = TextField('ISBN 13',[validate_isbn13])
    category = SelectField(lazy_gettext(u'Category'), choices=book_categories)
    submit = SubmitField(lazy_gettext(u'Save'))



@bp.route('/add', methods=['GET','POST'])
@login_required
def new_book():
    """
    Add a new book to the database
    """
    form = BookForm()

    if form.validate_on_submit():
        # save the album
        book = Book()
        save_changes(book, form, new=True)
        flash(lazy_gettext(u'Book created successfully!'),'success')
        return redirect('/')

    return render_template('books/new.html', form=form)



def save_changes( book, form, new = False):
    """
    Save the changes to a given book
    """
    import datetime

    book.title = form.title.data
    book.publisher = form.publisher.data
    book.author = form.author.data
    book.isbn10 = form.isbn10.data
    book.isbn13 = form.isbn13.data
    book.renter_id = ''
    book.rented_time = None
    book.category = form.category.data

    if new:
        # Add the book to the database
        db.session.add(book)

    db.session.commit()


class CategoryCol(Col):
    def td_format(self,content):
        values=dict(book_categories)
        if values[content] is not None:
            return values[content]
        else: 
            return lazy_gettext(u'Unknown Category')

class BookResults(Table):
    classes = ['table']
    id = Col('Id', show=False)
    title = Col(lazy_gettext(u'Title'))
    publisher = Col(lazy_gettext(u'Publisher'))
    author = Col(lazy_gettext(u'Author'))
    isbn10 = Col('ISBN 10')
    isbn13 = Col('ISBN 13')
    category = CategoryCol(lazy_gettext(u'Category'))
    renter_name = Col(lazy_gettext(u'Renter'))
    rented_time = DatetimeCol(lazy_gettext(u'Rented time'))
    rent = ButtonCol(lazy_gettext(u'Rent / Give Back'), '.rent', url_kwargs=dict(id='id'))


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    results = Book.query.all()
    table = BookResults(results, no_items=lazy_gettext(u'No books in the database'))
    if current_user.has_roles('Admin'):
        table.add_column('edit', LinkCol(lazy_gettext(u'Edit'),'.edit',url_kwargs=dict(id='id')))
        print(table)
    return render_template('books/index.html', table=table)

    
 
@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    search = BookSearchForm()
    if search.validate_on_submit():
        return search_results(search)
 
    return render_template('books/search.html', form=search)

@bp.route('/results')
@login_required
def search_results (search):
    results = []
    search_string = search.search.data

    if search_string:
        import re
        search_string_list = re.sub("[^\W]"," ",search_string).split()
        qry = db.session.query(Book).filter(Book.title == search_string)
        results = qry.all()
    else:
        qry = db.session.query(Book)
        results = qry.all()
 
    if not results:
        flash(lazy_gettext(u'No results found!'),'info')
        return redirect(url_for('search'))
    else:
        # display results
        table = BookResults(results)
        if current_user.has_roles('Admin'):
            table.add_column('edit', LinkCol(lazy_gettext(u'Edit'),'.edit',url_kwargs=dict(id='id')))
        table.border = True
        return render_template('books/results.html', table=table, form=search)

@bp.route('/item/<int:id>', methods=['GET', 'POST'])
@roles_required('Admin')
def edit(id):
    qry = db.session.query(Book).filter(Book.id==id)
    book = qry.first()

    if book:
        form = BookForm(formdata=request.form, obj=book)
        if request.method == 'POST' and form.validate():
            # Save modifications
            save_changes(book, form)
            flash(lazy_gettext(u'Book updated successfully!'),'success')
            return redirect('/')
        return render_template('books/edit_book.html', form=form)
    else:
        flash(lazy_gettext(u'ERROR Book #{id} doesn''t exist').format(id=id))
        return redirect(url_for('.index'))

@bp.route('/rent_item/<int:id>', methods=['GET', 'POST'])
@login_required
def rent(id):
    qry = db.session.query(Book).filter(Book.id==id)
    book = qry.first()

    if book:
        import datetime
        if book.renter_name == current_user.username:
            book.renter_name = None
            book.rented_time = None
            db.session.commit()
        elif book.renter_name is None:
            qry = db.session.query(User).filter(User.id==current_user.id)
            user = qry.first()
            book.renter_name = user.username
            book.rented_time = datetime.datetime.now()
            db.session.commit()
        else:
            flash(lazy_gettext(u'ERROR Book {title} is already rented by someone else.').format(title=book.title))
    else:
        flash(lazy_gettext(u'ERROR Book #{id} doesn''t exist').format(id=id))
    return redirect('/')