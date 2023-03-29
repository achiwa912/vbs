from flask import render_template, session, redirect, url_for, flash
from flask_login import current_user, login_required
from config import config
from . import main
from .. import db
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
    session["lwin"] = []
    session["index"] = 0
    session["url"] = url_for(".book", bk_id=bk_id)
    return render_template("book.html", bk=bk)


@main.route("/practice/<bk_id>/<ptype>")
@login_required
def practice(bk_id, ptype):
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
    fill_lwin(bk.id, ptype)
    session["url"] = url_for(".practice", bk_id=bk_id, ptype=ptype)
    word = Word.query.filter_by(id=session["lwin"][session["index"]]).first()
    prac = (
        Practice.query.filter_by(user_id=current_user.id)
        .filter_by(word_id=word.id)
        .first()
    )
    return render_template("practice.html", bk=bk, word=word, prac=prac, ptype=ptype)


@main.route("/practice-oncemore")
@login_required
def practice_oncemore():
    session["index"] += 1
    if session["index"] >= config["LWIN_SIZE"]:
        session["index"] = 0
    if "url" in session:
        return redirect(session["url"])
    return redirect(url_for(".index"))


@main.route("/practice-memorized/<ptype>/<plus>")
@login_required
def practice_memorized(ptype, plus):
    word_id = session["lwin"].pop(session["index"])
    practice = Practice.query.filter(
        Practice.word_id == word_id and Practice.user_id == current_user.id
    ).first()
    if ptype == 2:  # type Word
        practice.score_type += int(plus)
    elif ptype == 1:  # d2w
        practice.score_d2w += int(plus)
    else:  # w2d
        practice.score_w2d += int(plus)
    db.session.add(practice)
    db.session.commit()
    word = Word.query.filter_by(id=word_id).first()
    fill_lwin(word.book_id, ptype)
    if "url" in session:
        return redirect(session["url"])
    return redirect(url_for(".index"))
