from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    RadioField,
    BooleanField,
    IntegerField,
    FileField,
)
from wtforms.validators import DataRequired, EqualTo


class EditBookForm(FlaskForm):
    name = StringField("Book name", validators=[DataRequired()])
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
    delete = BooleanField("Delete")
    submit = SubmitField("Submit")


class LoadFileForm(FlaskForm):
    filename = FileField()
    submit = SubmitField("Submit")


class PracTypeForm(FlaskForm):
    word = StringField("Your answer?", render_kw={"autofocus": True})
    submit = SubmitField("Submit")


class RepeatForm(FlaskForm):
    word1 = StringField("", validators=[DataRequired()], render_kw={"autofocus": True})
    word2 = StringField(
        "", validators=[DataRequired(), EqualTo("word1", message="spell incorrect")]
    )
    word3 = StringField(
        "", validators=[DataRequired(), EqualTo("word1", message="spell incorrect")]
    )
    word4 = StringField(
        "", validators=[DataRequired(), EqualTo("word1", message="spell incorrect")]
    )
    submit = SubmitField("Submit")
