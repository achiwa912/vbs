import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from flask_login import UserMixin, AnonymousUserMixin, current_user
from . import db, login_manager
from config import config


class Practice(db.Model):
    __tablename__ = "practices"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey("words.id"), primary_key=True)
    score_w2d = db.Column(db.Integer, default=0)
    score_d2w = db.Column(db.Integer, default=0)
    score_type = db.Column(db.Integer, default=0)
    user = db.relationship("User", back_populates="words")

    def __init__(self, user_id, word_id):
        self.user_id = user_id
        self.word_id = word_id

    def __repr__(self):
        return (
            f"<Prac {self.word_id} {self.score_w2d}/{self.score_d2w}/{self.score_type}>"
        )


class Word(db.Model):
    __tablename__ = "words"
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(64))
    definition = db.Column(db.String(256))
    sample = db.Column(db.String(256), default="")
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))
    book = db.relationship("Book", back_populates="words")

    def __init__(self, word, definition, sample, book_id):
        self.word = word
        self.definition = definition
        self.sample = sample
        self.book_id = book_id
        db.session.add(self)

    def delete(self):
        prac = (
            Practice.query.filter_by(word_id=self.id)
            .filter_by(user_id=current_user.id)
            .first()
        )
        if prac:
            db.session.delete(prac)
        db.session.delete(self)
        db.session.commit()


subscriptions = db.Table(
    "subscriptions",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("book_id", db.Integer, db.ForeignKey("books.id")),
)


class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    createtime = db.Column(db.DateTime())
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    words = db.relationship("Word", back_populates="book")
    subscribers = db.relationship(
        "User", secondary=subscriptions, back_populates="books"
    )
    owner = db.relationship("User", back_populates="my_books")

    def __init__(self, name, owner_id):
        self.name = name
        self.owner_id = owner_id
        self.createtime = datetime.utcnow()
        db.session.add(self)

    def load_from_stream(self, stream):
        """
        Load word data from stream
        """
        for line in stream:
            llist = line.decode("utf8").split("\t")
            if len(llist) < 2:
                continue
            # same word in this book?
            if Word.query.filter_by(book_id=self.id).filter_by(word=llist[0]).first():
                continue
            if len(llist) > 2:
                word = Word(
                    llist[0].strip(), llist[1].strip(), llist[2].strip(), self.id
                )
            else:
                word = Word(llist[0].strip(), llist[1].strip(), "", self.id)
            db.session.add(word)
        db.session.commit()

    def load_from_file(self, file_path):
        """
        Load word data from a file
        """
        with open(file_path) as fpnt:
            for line in fpnt:
                llist = line.split("\t")
                if len(llist) < 2:
                    continue
                # same word in this book?
                if (
                    Word.query.filter_by(book_id=self.id)
                    .filter_by(word=llist[0])
                    .first()
                ):
                    continue
                if len(llist) > 2:
                    word = Word(
                        llist[0].strip(), llist[1].strip(), llist[2].strip(), self.id
                    )
                else:
                    word = Word(llist[0].strip(), llist[1].strip(), "", self.id)
                db.session.add(word)
            db.session.commit()

    def delete(self):
        for word in self.words:
            word.delete()
        db.session.delete(self)
        db.session.commit()


class Permission:
    VIEW = 1
    WRITE = 2
    ADMIN = 16


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship("User", backref="role", lazy="dynamic")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.permissions is None:
            self.permissons = 0

    @staticmethod
    def insert_roles():
        roles = {
            "User": [Permission.VIEW, Permission.WRITE],
            "Administrator": [Permission.VIEW, Permission.WRITE, Permission.ADMIN],
        }
        default_role = "User"
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = role.name == default_role
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return f"<Role {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    password_hash = db.Column(db.String(128))
    words = db.relationship("Practice", back_populates="user")
    my_books = db.relationship("Book", back_populates="owner")
    books = db.relationship(
        "Book", secondary=subscriptions, back_populates="subscribers"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.role is None:
            if self.username == "admin":
                self.role = Role.query.filter_by(name="Administrator").first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute.")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def __repr__(self):
        return f"<User {self.username}>"


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def fill_lwin(book_id, ptype):
    """
    fill learning window (lwin)
    lwin - list of word_id
    ptype - '0': w2d, '1': d2w, '2': type
    """
    addnum = config["LWIN_SIZE"] - len(session["lwin"])
    if addnum <= 0:
        return
    if int(ptype) == 2:  # type
        prac_lst = (
            Practice.query.join(User, User.id == Practice.user_id)
            .join(Word, Word.id == Practice.word_id)
            .filter(Word.book_id == book_id)
            .filter(User.id == current_user.id)
            .order_by(Practice.score_type)
            .group_by(Practice.score_type)
            .all()
        )
        prac_cntlst = [prac.score_type for prac in prac_lst]
    elif int(ptype) == 1:  # d2w
        prac_lst = (
            Practice.query.join(User, User.id == Practice.user_id)
            .join(Word, Word.id == Practice.word_id)
            .filter(Word.book_id == book_id)
            .filter(User.id == current_user.id)
            .order_by(Practice.score_d2w)
            .group_by(Practice.score_d2w)
            .all()
        )
        prac_cntlst = [prac.score_d2w for prac in prac_lst]
    else:  # w2d
        prac_lst = (
            Practice.query.join(User, User.id == Practice.user_id)
            .join(Word, Word.id == Practice.word_id)
            .filter(Word.book_id == book_id)
            .filter(User.id == current_user.id)
            .order_by(Practice.score_w2d)
            .group_by(Practice.score_w2d)
            .all()
        )
        prac_cntlst = [prac.score_w2d for prac in prac_lst]
    """
    Wow, I had a really tough bug here.
    NEVER directly update session context variable if it's a list.
    I did like session['lwin'].append(..) but it reverted back to
    previous list after a redirect.
    https://stackoverflow.com/questions/61972873/flask-session-lost-data
    """
    lwin = session["lwin"][:]
    for prac_cnt in prac_cntlst:
        if int(ptype) == 2:  # type word
            practices = (
                Practice.query.join(User, User.id == Practice.user_id)
                .join(Word, Word.id == Practice.word_id)
                .filter(Word.book_id == book_id)
                .filter(User.id == current_user.id)
                .filter(Practice.score_type == prac_cnt)
                .all()
            )
        elif int(ptype) == 1:  # d2w
            practices = (
                Practice.query.join(User, User.id == Practice.user_id)
                .join(Word, Word.id == Practice.word_id)
                .filter(Word.book_id == book_id)
                .filter(User.id == current_user.id)
                .filter(Practice.score_d2w == prac_cnt)
                .all()
            )
        else:  # w2d
            practices = (
                Practice.query.join(User, User.id == Practice.user_id)
                .join(Word, Word.id == Practice.word_id)
                .filter(Word.book_id == book_id)
                .filter(User.id == current_user.id)
                .filter(Practice.score_w2d == prac_cnt)
                .all()
            )
        random.shuffle(practices)
        for prac in practices:
            word = Word.query.filter_by(id=prac.word_id).first()
            if word.id not in lwin:
                lwin.append(word.id)
                if len(lwin) >= config["LWIN_SIZE"]:
                    session["lwin"] = lwin
                    return
        session["lwin"] = lwin


def create_practices(book, user):
    """
    create practices for the book and the user
    """
    words = Word.query.filter_by(book_id=book.id).all()
    for word in words:
        if not Practice.query.filter(
            Practice.word_id == word.id and Practice.user_id == user.id
        ).first():
            db.session.add(Practice(user.id, word.id))
    db.session.commit()
