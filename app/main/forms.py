from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField, BooleanField, IntegerField
from wtforms.validators import DataRequired


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
