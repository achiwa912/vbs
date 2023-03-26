from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
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


subscriptions = db.Table(
    "subscriptions",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("book_id", db.Integer, db.ForeignKey("books.id")),
)


class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    words = db.relationship("Word", back_populates="book")
    subscribers = db.relationship(
        "User", secondary=subscriptions, back_populates="books"
    )
    owner = db.relationship("User", back_populates="my_books")

    def __init__(self, name, owner_id):
        self.name = name
        self.owner_id = owner_id
        db.session.add(self)

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
                    Word.query.join(Book, Book.id == Word.book_id)
                    .filter(Word.word == llist[0])
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
