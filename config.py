import os
import json

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = "sglm2j4tm2j8l5kwq09uh"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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

try:
    secrets = {}
    with open("secrets.json") as f:
        secrets = json.load(f)
except Exception as e:
    pass

config = config_base | secrets
