from flask import render_template, session
from flask_login import current_user
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
