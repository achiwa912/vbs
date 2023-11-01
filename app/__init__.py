from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

bootstrap = Bootstrap5()
mail = Mail()
moment = Moment()
db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app(config_name):
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = config["UPLOAD_FOLDER"]
    app.config["ADMIN_USER"] = config["ADMIN_USER"]
    app.config["ADMIN_PASS"] = config["ADMIN_PASS"]
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587  # 465 for SSL
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USE_SSL"] = False
    app.config["MAIL_USERNAME"] = config["MAIL_USERNAME"]
    app.config["MAIL_PASSWORD"] = config["MAIL_PASSWORD"]
    app.config["SECRET_KEY"] = config["SECRET_KEY"]
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # up to 1MB
    app.config["UPLOAD_EXTENSIONS"] = [".txt"]
    app.config.from_object(config[config_name])
    app.config["BOOTSTRAP_BOOTSWATCH_THEME"] = "litera"
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)

    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    return app
