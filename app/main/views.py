from flask import render_template, session, redirect, url_for, flash
from flask_login import current_user, login_required
from . import main
from ..models import Book


@main.route("/", methods=["GET", "POST"])
def index():
    my_books = []
    if current_user.is_authenticated:
        my_books = Book.query.filter_by(owner_id=current_user.id).all()
    return render_template(
        "index.html",
        name=session.get("name"),
        known=session.get("known", False),
        my_books=my_books,
    )


@main.route("/book/<bk_id>", methods=["GET", "POST"])
@login_required
def book(bk_id):
    bk = Book.query.filter_by(id=bk_id).first_or_404()
    session["url"] = url_for(".book", bk_id=bk_id)
    return render_template("book.html", bk=bk)
