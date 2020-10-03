from app import db
from flask_wtf import FlaskForm
from wtforms import Form, TextField, SelectField, SubmitField, validators, ValidationError
from flask import (
        Blueprint, flash, g, redirect, render_template, request, url_for
        )
from werkzeug.exceptions import abort
from auth import login_required, User
from flask_table import Table, Col, LinkCol, ButtonCol, DatetimeCol
from flask_babelex import gettext, ngettext, _
from flask_babelex import lazy_gettext as _l
from flask_user import current_user, login_required, roles_required
from sqlalchemy import or_
import enum

bp = Blueprint('books', __name__, url_prefix='/books')

book_categories=[('textbook', _l(u'Textbook')),
                ('grammar_and_vocabulary', _l(u'Grammar and Vocabulary')),
                ('literrature', _l(u'Literature')),
                ('text_commentaries', _l(u'Text Commentaries and Teaching Material')),
                ('didactic_pedagogy', _l(u'Didactics and Pedagogy')),
                ('magazine', _l(u'Magazine')),
                ('game', _l(u'Game'))
               ]

class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String, nullable = False )
    publisher = db.Column(db.String, nullable = False)
    author = db.Column(db.String, nullable = True)
    isbn13 = db.Column(db.String(13), nullable = False)
    # renter information's:
    renter_name = db.Column(db.String, db.ForeignKey("users.username"), nullable =True)
    rented_time = db.Column(db.DateTime, nullable = True)
    renter = db.relationship("User", backref=db.backref("books", order_by = id), lazy = True)
    category = db.Column(db.String, nullable = False)




class BookSearchForm(FlaskForm):
    search = TextField('')
    submit = SubmitField(_l(u'Search'))


def validate_isbn13(form, field):
    if field.data:
        if len(field.data) != 13:
            raise ValidationError(_l(u'ISBN 13 must be 10 character long'))
        if not field.data.isdigit():
            raise ValidationError(_l(u'ISBN 13 must contain only numeric characters'))

class BookForm(FlaskForm):
    title = TextField(_l('Title'),[validators.InputRequired()])
    publisher = TextField(_l('Publisher'),[validators.InputRequired()])
    author = TextField(_l('Author'))
    isbn13 = TextField('ISBN 13',[validate_isbn13])
    category = SelectField(_l('Category'), choices=book_categories)
    submit = SubmitField(_l('Save'))



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
        flash(_l(u'Book created successfully!'),'success')
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
    book.isbn13 = form.isbn13.data
    book.renter_name = ''
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
            return _l(u'Unknown Category')

class BookResults(Table):
    classes = ['table']
    id = Col('Id', show=False)
    title = Col(_l(u'Title'))
    publisher = Col(_l(u'Publisher'))
    author = Col(_l(u'Author'))
    isbn13 = Col('ISBN 13')
    category = CategoryCol(_l(u'Category'))
    renter_name = Col(_l(u'Renter'))
    rented_time = DatetimeCol(_l(u'Rented time'))
    rent = ButtonCol(_l(u'Rent / Give Back'), '.rent', url_kwargs=dict(id='id'))

@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    results = Book.query.all()
    table = BookResults(results)#, no_items=_l(u'No books in the database'))
    if current_user.has_roles('Admin'):
        table.add_column('edit', LinkCol(_l(u'Edit'),'.edit',url_kwargs=dict(id='id')))
    return render_template('books/index.html', table=table)

    
 
@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    search = BookSearchForm()
    if search.validate_on_submit():
        return redirect(url_for('.search_results', search_string=search.search.data))
 
    return render_template('books/search.html', form=search)

@bp.route('/results/<string:search_string>', methods=['GET', 'POST'])
@bp.route('/results/', methods=['GET', 'POST'])
@bp.route('/results', methods=['GET', 'POST'])
@login_required
def search_results(search_string=None):
    results = []
    search = BookSearchForm()

    if search.validate_on_submit():
        return redirect(url_for('.search_results', search_string=search.search.data))

    if search_string:
        search_string_list = search_string.split(' ')
        qry=Book.query.filter(Book.title.contains(search_string))
        for string in search_string_list:
            subquery = Book.query.filter(or_(Book.title.contains(string),
                                        Book.author.contains(string),
                                        Book.publisher.contains(string),
                                        Book.isbn13.contains(string),
                                        Book.category.contains(string)))
            qry = qry.union(subquery)
        results = qry.all()
    else:
        results = Book.query.all()
 
    if not results:
        message = gettext(u'No results found!') 
        flash(message,'info')
        return redirect(url_for('.search'))
    else:
        # display results
        table = BookResults(results)
        search.search.data = search_string
        if current_user.has_roles('Admin'):
            table.add_column('edit', LinkCol(_l(u'Edit'),'.edit',url_kwargs=dict(id='id')))
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
            flash(_l(u'Book updated successfully!'),'success')
            return redirect('/')
        return render_template('books/edit_book.html', form=form)
    else:
        flash(_l(u'ERROR Book #{id} doesn''t exist').format(id=id))
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
            flash(_l(u'ERROR Book {title} is already rented by someone else.').format(title=book.title))
    else:
        flash(_l(u'ERROR Book #{id} doesn''t exist').format(id=id))
    return redirect(url_for('.index'))