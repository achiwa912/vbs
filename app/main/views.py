import os
import json
from flask import render_template, session, redirect, url_for, flash, request
from flask import Response, jsonify
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
    ReadAloudForm,
)
from .. import db
from ..models import Book, Word, Practice, User, fill_lwin, create_practices

from gtts import gTTS
from mutagen.mp3 import MP3


@main.route("/", methods=["GET", "POST"])
def index():
    form = ReadAloudForm()
    if config["debug"]:
        session["debug"] = True
    else:
        session["debug"] = False
    my_books = []
    if current_user.is_authenticated:
        my_books = Book.query.filter_by(owner_id=current_user.id).all()
    if form.validate_on_submit():
        text = form.text.data[:1024]

        path = f"{current_user.username}.mp3"
        try:
            tts = gTTS(text, lang="en")
            tts.save(path)
        except Exception as e:
            flash(f"Google tts returned an error: {e}", "error")
            return redirect(url_for(".index"))

        try:
            audio = MP3(path)
            length = int(audio.info.length * 1000)
        except:
            length = 3000  # 3 sec
        session["audio_len"] = length
        session["username"] = current_user.username

        return redirect(
            url_for(".pronounce", username=current_user.username, word_id=0)
        )

    return render_template(
        "index.html",
        name=session.get("name"),
        known=session.get("known", False),
        my_books=my_books,
        form=form,
    )


@main.route("/book/<bk_id>", methods=["GET", "POST"])
@login_required
def book(bk_id):
    bk = Book.query.filter_by(id=bk_id).first_or_404()
    session["lwin"] = []
    session["index"] = 0
    session["tmp_score"] = 0
    session["tmp_count"] = 0
    session["url"] = url_for(".book", bk_id=bk_id)
    return render_template("book.html", bk=bk)


@main.route("/practice/<bk_id>/<ptype>", methods=["GET", "POST"])
@login_required
def practice(bk_id, ptype):
    bk = Book.query.filter_by(id=bk_id).first_or_404()
    session["ptype"] = ptype
    session["word_lang"] = bk.word_lang

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
                session["tmp_count"] += 1
            else:
                session["index"] += 1
                if session["index"] >= len(session["lwin"]):
                    session["index"] = 0
                correct = False
                flash(f"Incorrect! -- Let's type the word 4 times", "error")
                session["tmp_count"] += 1
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


@main.route("/practice-oncemore/<ptype>")
@login_required
def practice_oncemore(ptype):
    word_id = session["lwin"][session["index"]]
    practice = Practice.query.filter(
        Practice.word_id == word_id and Practice.user_id == current_user.id
    ).first()
    session["tmp_count"] += 1
    if int(ptype) == 2:  # type Word
        practice.ng_type += 1
    elif int(ptype) == 1:  # d2w
        practice.ng_d2w += 1
    else:  # w2d
        practice.ng_w2d += 1
    db.session.add(practice)
    db.session.commit()
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
    session["tmp_count"] += 1
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
            bk.word_lang = form.word_lang.data
            db.session.add(bk)
            db.session.commit()
            flash(f"Renamed to { bk.name }", "success")
        return redirect(url_for(".index"))
    bk = Book.query.filter_by(id=bk_id).first()
    if not bk:
        flash(f"Book id={bk_id} doesn't exist", "error")
        return redirect(url_for(".index"))
    form.name.data = bk.name
    form.word_lang.data = bk.word_lang
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
            prac.ng_w2d = form.ng_w2d.data
            prac.ng_d2w = form.ng_d2w.data
            prac.ng_type = form.ng_type.data
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
        form.ng_w2d.data = prac.ng_w2d
        form.ng_d2w.data = prac.ng_d2w
        form.ng_type.data = prac.ng_type
    else:
        form.score_w2d.data = 0
        form.score_d2w.data = 0
        form.score_type.data = 0
        form.ng_w2d.data = 0
        form.ng_d2w.data = 0
        form.ng_type.data = 0
    return render_template("editword.html", form=form, word=word)


@main.route("/pronounce/<username>")
@login_required
def pronounce(username):
    path = f"{current_user.username}.mp3"

    try:
        audio = MP3(path)
        length = int(audio.info.length * 1000)
    except:
        length = 3000  # 3 sec
    session["audio_len"] = length + 400
    session["username"] = current_user.username

    def generate():
        path = f"{username}.mp3"
        with open(path, "rb") as fmp3:
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


@main.route("/import", methods=["GET", "POST"])
@login_required
def import_restore():
    """
    Import and restore books and progress from a JSON file
    """
    form = LoadFileForm()
    if request.method == "POST":
        uploaded_file = request.files["file"]
        filename = secure_filename(uploaded_file.filename)
        if filename != "":
            file_ext = os.path.splitext(filename)[1]
            if file_ext.lower() != ".json":
                return "Invalid file", 400
            try:
                idic = json.load(uploaded_file)
            except:
                return "Invalid file contents", 400
            word_lang_dic = {}
            for book_name, word_items in idic.items():
                if book_name == "@word_lang@":
                    word_lang_dic = word_items
                    continue
                bk = (
                    Book.query.filter_by(name=book_name)
                    .filter_by(owner_id=current_user.id)
                    .first()
                )
                if not bk:
                    bk = Book(book_name, current_user.id)
                    db.session.add(bk)
                    db.session.commit()
                for word_item in word_items:
                    word = (
                        Word.query.filter_by(word=word_item[0])
                        .filter_by(book_id=bk.id)
                        .first()
                    )
                    if not word:
                        word = Word(word_item[0], word_item[1], word_item[2], bk.id)
                        db.session.add(word)
                        db.session.commit()
                        prac = Practice(current_user.id, word.id)
                        prac.score_w2d = word_item[3]
                        prac.score_d2w = word_item[4]
                        prac.score_type = word_item[5]
                        if len(word_item) > 6:  # has ng_xx values?
                            prac.ng_w2d = word_item[6]
                            prac.ng_d2w = word_item[7]
                            prac.ng_type = word_item[8]
                        db.session.add(prac)
                        db.session.commit()
                    else:
                        word.definition = word_item[1]
                        word.sample = word_item[2]
                        db.session.add(word)
                        prac = (
                            Practice.query.filter_by(word_id=word.id)
                            .filter_by(user_id=current_user.id)
                            .first()
                        )
                        if not prac:
                            prac = Practice(current_user.id, word.id)
                        prac.score_w2d = max(word_item[3], prac.score_w2d)
                        prac.score_d2w = max(word_item[4], prac.score_d2w)
                        prac.score_type = max(word_item[5], prac.score_type)
                        if len(word_item) > 6:  # has ng_xx values?
                            prac.ng_w2d = max(word_item[6], prac.ng_w2d)
                            prac.ng_d2w = max(word_item[7], prac.ng_d2w)
                            prac.ng_type = max(word_item[8], prac.ng_type)
                        db.session.add(prac)
                        db.session.commit()
            for book_name, word_lang in word_lang_dic.items():
                bk = (
                    Book.query.filter_by(name=book_name)
                    .filter_by(owner_id=current_user.id)
                    .first()
                )
                if bk:
                    bk.word_lang = word_lang
                    db.session.add(bk)
                    db.session.commit()
        else:
            return "", 204  # No content
        return redirect(url_for(".index"))
    return render_template("import.html", form=form)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"txt"}


@main.route("/export")
@login_required
def export():
    """
    Export books and progress to a local JSON file
    """
    exp_dic = {}
    word_lang_dic = {}
    my_books = Book.query.filter_by(owner_id=current_user.id).all()
    for my_book in my_books:
        exp_dic[my_book.name] = []
        words = Word.query.filter_by(book_id=my_book.id).all()
        for word in words:
            prac = (
                Practice.query.filter_by(user_id=current_user.id)
                .filter_by(word_id=word.id)
                .first()
            )
            if prac:
                exp_dic[my_book.name].append(
                    (
                        word.word,
                        word.definition,
                        word.sample,
                        prac.score_w2d,
                        prac.score_d2w,
                        prac.score_type,
                        prac.ng_w2d,
                        prac.ng_d2w,
                        prac.ng_type,
                    )
                )
            else:
                exp_dic[my_book.name].append(
                    (word.word, word.definition, word.sample, 0, 0, 0)
                )
        word_lang_dic[my_book.name] = my_book.word_lang
        exp_dic["@word_lang@"] = word_lang_dic
    exp_json = json.dumps(exp_dic)
    return Response(
        exp_json,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=vocabull.json"},
    )
