import os
import json

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY = "sglm2j4tm2j8l5kwq09uh"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.googlemail.com")
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
    MAIL_SUBJECT_PREFIX = "[vocaBull]"
    MAIL_SENDER = "vocaBull Admin <hojimelon727@gmail.com>"

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "vbs-dev.sqlite")


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "vbs.sqlite")


config_base = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
    "UPLOAD_FOLDER": "~/tmp",
    "UPLOAD_EXTENSIONS": [".txt"],
    "LWIN_SIZE": 10,  # Learning window size
    "debug": False,
}

secrets = {}
with open("secrets.json") as f:
    secrets = json.load(f)

config = config_base | secrets
