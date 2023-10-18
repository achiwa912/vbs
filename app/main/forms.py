from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    StringField,
    SubmitField,
    RadioField,
    BooleanField,
    IntegerField,
    TextAreaField,
)
from wtforms.validators import DataRequired, EqualTo


class EditBookForm(FlaskForm):
    name = StringField("Book name:", validators=[DataRequired()])
    # lang = RadioField(
    #     label="Word lang:",
    #     choices=[
    #         ("en-US", "English (US)"),
    #         ("en-GB", "English (UK)"),
    #         ("ja-JP", "日本語"),
    #         ("es-ES", "español"),
    #         ("fr-FR", "français"),
    #         ("", "Other"),
    #     ],
    # )
    word_lang = StringField(
        "Language to pronounce (eg, en-US, ja-JP):", validators=[DataRequired()]
    )
    delete = BooleanField("Delete")
    submit = SubmitField("Submit")


class AddWordForm(FlaskForm):
    word = StringField("Word", validators=[DataRequired()])
    definition = StringField("Definition", validators=[DataRequired()])
    sample = StringField("Sample usage")
    submit = SubmitField("Submit")


class EditWordForm(FlaskForm):
    word = StringField("Word", validators=[DataRequired()])
    definition = StringField("Definition", validators=[DataRequired()])
    sample = StringField("Sample usage")
    score_w2d = IntegerField("Score word to def")
    score_d2w = IntegerField("Score def to word")
    score_type = IntegerField("Score type word")
    ng_w2d = IntegerField("Once more word to def")
    ng_d2w = IntegerField("Once more def to word")
    ng_type = IntegerField("Once more type word")
    delete = BooleanField("Delete")
    submit = SubmitField("Submit")


class LoadFileForm(FlaskForm):
    filename = FileField()
    submit = SubmitField("Submit")


class PracTypeForm(FlaskForm):
    word = StringField(
        "Your answer?", render_kw={"autofocus": True, "autocomplete": "off"}
    )
    submit = SubmitField("Submit")


class RepeatForm(FlaskForm):
    word1 = StringField(
        "",
        validators=[DataRequired()],
        render_kw={"autofocus": True, "autocomplete": "off"},
    )
    word2 = StringField(
        "",
        validators=[DataRequired(), EqualTo("word1", message="spell incorrect")],
        render_kw={"autocomplete": "off"},
    )
    word3 = StringField(
        "",
        validators=[DataRequired(), EqualTo("word1", message="spell incorrect")],
        render_kw={"autocomplete": "off"},
    )
    word4 = StringField(
        "",
        validators=[DataRequired(), EqualTo("word1", message="spell incorrect")],
        render_kw={"autocomplete": "off"},
    )
    submit = SubmitField("Submit")


class ReadAloudForm(FlaskForm):
    text = TextAreaField("", validators=[DataRequired()])
    submit = SubmitField("Submit")
