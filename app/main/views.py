from flask import render_template, session, redirect, url_for, flash
from flask_login import current_user, login_required
from config import config
from . import main
from .forms import EditBookForm
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
    if int(ptype) == 2:  # type Word
        practice.score_type += int(plus)
    elif int(ptype) == 1:  # d2w
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


@main.route("/add-book", methods=["GET", "POST"])
@login_required
def add_book():
    """
    Add a vacant book
    """
    form = EditBookForm()
    if form.validate_on_submit():
        bk = Book.query.filter_by(name=form.name.data).first()
        if bk:
            flash(f"Book: { form.name.data } already exists", "error")
            return redirect(url_for(".index"))
        bk = Book(form.name.data, current_user.id)
        db.session.add(bk)
        db.session.commit()
        flash(f"Book: { bk.name } created", "success")
        return redirect(url_for(".index"))
    return render_template("editbook.html", form=form, bk=None)


@main.route("/edit-book/<bk_id>", methods=["GET", "POST"])
@login_required
def edit_book(bk_id):
    """
    Edit book name or delete the book
    """
    form = EditBookForm()
    if form.validate_on_submit():
        bk = Book.query.filter_by(id=bk_id).first()
        if not bk:
            flash(f"Book id={bk_id} doesn't exist", "error")
            return redirect(url_for(".index"))
        if form.delete.data:
            db.session.delete(bk)
            db.session.commit()
            flash(f"Book: { bk.name } deleted", "success")
        else:
            bk.name = form.name.data
            db.session.add(bk)
            db.session.commit()
            flash(f"Renamed to { bk.name }", "success")
        return redirect(url_for(".index"))
    bk = Book.query.filter_by(id=bk_id).first()
    if not bk:
        flash(f"Book id={bk_id} doesn't exist", "error")
        return redirect(url_for(".index"))
    form.name.data = bk.name
    return render_template("editbook.html", form=form, bk=bk)
