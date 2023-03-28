from flask import render_template, session, redirect, url_for, flash
from flask_login import current_user, login_required
from . import main
from ..models import Book, Word, Practice, User, fill_lwin, create_practices


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


@main.route("/practice-w2d/<bk_id>", methods=["GET", "POST"])
@login_required
def practice_w2d(bk_id):
    bk = Book.query.filter_by(id=bk_id).first_or_404()

    # create practices for the book & user
    numprac = (
        Practice.query.join(User, User.id == Practice.user_id)
        .join(Word, Word.id == Practice.word_id)
        .filter(Word.book_id == bk_id and User.id == current_user.id)
        .count()
    )
    numword = Word.query.filter_by(book_id=bk_id).count()
    if numprac < numword:
        create_practices(bk, current_user)
    if not session.get("lwin"):
        session["lwin"] = []
    if not session.get("index"):
        session["index"] = 0
    fill_lwin(session["lwin"], session["index"], bk, 0)
    session["url"] = url_for(".practice_w2d", bk_id=bk_id)
    word = Word.query.filter_by(id=session["lwin"][session["index"]][0]).first()
    return render_template("practice-w2d.html", bk=bk, word=word)
