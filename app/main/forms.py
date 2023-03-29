from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField, BooleanField
from wtforms.validators import DataRequired


class EditBookForm(FlaskForm):
    name = StringField("Book name", validators=[DataRequired()])
    delete = BooleanField("Delete")
    submit = SubmitField("Submit")
