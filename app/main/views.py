import os
from flask import render_template, session, redirect, url_for, flash, request
from flask import Response
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from config import config
from . import main
from .forms import (
    EditBookForm,
    EditWordForm,
    AddWordForm,
    LoadFileForm,
    PracTypeForm,
    RepeatForm,
)
from .. import db
from ..models import Book, Word, Practice, User, fill_lwin, create_practices
from gtts import gTTS


@main.route("/", methods=["GET", "POST"])
def index():
    if config["debug"]:
        session["debug"] = True
    else:
        session["debug"] = False
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
    session["tmp_score"] = 0
    session["url"] = url_for(".book", bk_id=bk_id)
    return render_template("book.html", bk=bk)


@main.route("/practice/<bk_id>/<ptype>", methods=["GET", "POST"])
@login_required
def practice(bk_id, ptype):
    bk = Book.query.filter_by(id=bk_id).first_or_404()
    session["ptype"] = ptype

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
    if "url_rep" in session:
        del session["url_rep"]
    word = Word.query.filter_by(id=session["lwin"][session["index"]]).first()
    prac = (
        Practice.query.filter_by(user_id=current_user.id)
        .filter_by(word_id=word.id)
        .first()
    )
    if int(ptype) == 2:  # type word
        form = PracTypeForm()
        if form.validate_on_submit():
            if form.word.data.strip() == word.word:
                prac.score_type += 1
                db.session.add(prac)
                db.session.commit()
                session["lwin"].pop(session["index"])
                fill_lwin(bk.id, int(ptype))
                correct = True
                flash(f"Correct! -- type the word 4 times, anyway", "success")
                session["tmp_score"] += 1
            else:
                session["index"] += 1
                if session["index"] >= len(session["lwin"]):
                    session["index"] = 0
                correct = False
                flash(f"Incorrect! -- Let's type the word 4 times", "error")
            return redirect(f"/repeat/{word.id}/{correct}")
        return render_template(
            "practice-type.html", bk=bk, word=word, prac=prac, form=form
        )
    return render_template("practice.html", bk=bk, word=word, prac=prac, ptype=ptype)


@main.route("/repeat/<wd_id>/<correct>", methods=["GET", "POST"])
@login_required
def repeat(wd_id, correct):
    word = Word.query.filter_by(id=wd_id).first()
    bk = Book.query.filter_by(id=word.book_id).first()
    prac = (
        Practice.query.filter_by(word_id=word.id)
        .filter_by(user_id=current_user.id)
        .first()
    )
    form = RepeatForm()
    if form.validate_on_submit():
        if "url" in session:
            return redirect(session["url"])
        return redirect(url_for(".index"))
    session["url_rep"] = url_for(".repeat", wd_id=wd_id, correct=correct)
    return render_template(
        "repeat.html", bk=bk, word=word, prac=prac, form=form, correct=correct
    )


@main.route("/practice-oncemore")
@login_required
def practice_oncemore():
    session["index"] += 1
    if session["index"] >= len(session["lwin"]):
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
    session["tmp_score"] += 1
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
            bk.delete()
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


@main.route("/add-word/<bk_id>", methods=["GET", "POST"])
@login_required
def add_word(bk_id):
    """
    Add a new word
    """
    form = AddWordForm()
    if form.validate_on_submit():
        word = Word(
            form.word.data.strip(),
            form.definition.data.strip(),
            form.sample.data.strip(),
            bk_id,
        )
        db.session.add(word)
        db.session.commit()
        flash(f"Word: {word.word} added", "success")
        if "url" in session:
            return redirect(session["url"])
        return redirect(url_for(".index"))
    return render_template("addword.html", form=form)


@main.route("/edit-word/<wd_id>", methods=["GET", "POST"])
@login_required
def edit_word(wd_id):
    """
    Edit (or delete) word
    """
    form = EditWordForm()
    word = Word.query.filter_by(id=wd_id).first()
    prac = (
        Practice.query.filter_by(word_id=word.id)
        .filter_by(user_id=current_user.id)
        .first()
    )
    if form.validate_on_submit():
        if not word:
            flash(f"Word id={wd_id} doesn't exist", "error")
            if "url_rep" in session:
                urlrep = session["url_rep"]
                session["url_rep"] = ""
                return redirect(urlrep)
            if "url" in session:
                return redirect(session["url"])
            return redirect(url_for(".index"))
        if form.delete.data:
            book = Book.query.filter_by(id=word.book_id).first()
            word.delete()
            session["lwin"].pop(session["index"])
            if session["index"] >= len(session["lwin"]):
                session["index"] = 0
            flash(f"Word {word.word} deleted", "success")
            if "url" in session and len(book.words) > 0:
                return redirect(
                    url_for(".practice", bk_id=book.id, ptype=session["ptype"])
                )
            return redirect(url_for(".index"))
        word.word = form.word.data.strip()
        word.definition = form.definition.data.strip()
        word.sample = form.sample.data.strip()
        db.session.add(word)

        if prac:
            prac.score_w2d = form.score_w2d.data
            prac.score_d2w = form.score_d2w.data
            prac.score_type = form.score_type.data
            db.session.add(prac)
        db.session.commit()
        flash(f"Word: {word.word} updated", "success")
        if "url_rep" in session:
            urlrep = session["url_rep"]
            session["url_rep"] = ""
            return redirect(urlrep)
        if "url" in session:
            return redirect(session["url"])
        return redirect(url_for(".index"))
    form.word.data = word.word
    form.definition.data = word.definition
    form.sample.data = word.sample
    if prac:
        form.score_w2d.data = prac.score_w2d
        form.score_d2w.data = prac.score_d2w
        form.score_type.data = prac.score_type
    else:
        form.score_w2d.data = 0
        form.score_d2w.data = 0
        form.score_type.data = 0
    return render_template("editword.html", form=form, word=word)


@main.route("/pronounce/<wd_id>")
@login_required
def pronoucne(wd_id):
    word = Word.query.filter_by(id=wd_id).first()
    tts = gTTS(word.word, lang="en")
    tts.save("tmp.mp3")

    def generate():
        with open("tmp.mp3", "rb") as fmp3:
            data = fmp3.read(1024)
            while data:
                yield data
                data = fmp3.read(1024)

    return Response(generate(), mimetype="audio/mpeg")


@main.route("/load-file/<bk_id>", methods=["GET", "POST"])
@login_required
def load_file(bk_id):
    """
    Load words from a file
    """
    form = LoadFileForm()
    if request.method == "POST":
        uploaded_file = request.files["file"]
        filename = secure_filename(uploaded_file.filename)
        if filename != "":
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in config["UPLOAD_EXTENSIONS"]:
                return "Invalid file", 400
            bk = Book.query.filter_by(id=bk_id).first()
            if not bk:
                flash(f"Book id={bk_id} not found", "error")
                if "url" in session:
                    return redirect(session["url"])
                return redirect(url_for(".index"))
            bk.load_from_stream(uploaded_file.stream)
        else:
            return "", 204
        if "url" in session:
            return redirect(session["url"])
        return redirect(url_for(".index"))
    return render_template("loadfile.html", form=form, bk_id=bk_id)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"txt"}
