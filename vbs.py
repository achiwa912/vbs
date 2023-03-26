import os
from app import create_app, db
from app.models import User, Role, Book

app = create_app(os.getenv("FLASK_CONFIG") or "default")


@app.shell_context_processor
def make_shell_context():
    return dict(db=db)


@app.cli.command()
def initial_setup():
    """create DB tables"""
    db.create_all()
    Role.insert_roles()


@app.cli.command()
def test_load():
    user = User.query.filter_by(username="kachiwa").first()
    book = Book("barron", user.id)
    book.load_from_file("ba.txt")
