from flask_nav import Nav
from flask_nav.elements import Navbar, View, Subgroup,Separator
from flask import (
        Blueprint, flash, g, redirect, render_template, request, url_for
        )
from auth import register, userlist
from books import index, search, new_book
from flask_babelex import gettext
from flask_user import current_user

nav = Nav()


@nav.navigation()
def mynavbar():
    if current_user.is_anonymous:
        navbar = Navbar(
            '',
            View(gettext(u'Login'),'user.login')
        )
    elif current_user.has_roles('Admin'):
        navbar = Navbar(
            '',
            View(gettext(u'Home'),'books.index'),
            Subgroup(
                gettext(u'Books'),
                View(gettext(u'New Book'), 'books.new_book'),
                View(gettext(u'List'), 'books.index'),
                View(gettext(u'Search'), 'books.search'),
            ),
            Subgroup(
                current_user.username,
                View(gettext(u'Add user'), 'auth.register'),
                View(gettext(u'User list'), 'auth.userlist'),
                View(gettext(u'Show Barcde'), 'auth.barcode',userid=current_user.id),
                View(gettext(u'Edit password'), 'auth.edit',userid=current_user.id),
                Separator(),
                View(gettext(u'Logout'),'user.logout'),
            ),
        )
    else:
        navbar = Navbar(
            '',
            View(gettext(u'Home'),'books.index'),
            Subgroup(
                gettext(u'Books'),
                View(gettext(u'List'), 'books.index'),
                View(gettext(u'Search'), 'books.search'),
            ),
            Subgroup(
                current_user.username,
                View(gettext(u'Show Barcde'), 'auth.barcode', userid=current_user.id),
                View(gettext(u'Edit password'), 'auth.edit', userid=current_user.id),
                Separator(),
                View(gettext(u'Logout'),'user.logout'),
            ),
        )

    return navbar

