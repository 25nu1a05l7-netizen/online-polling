from datetime import datetime, timedelta

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateTimeLocalField, EmailField, HiddenField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")


class PollForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    mode = SelectField("Voting Mode", choices=[("quick", "Quick Poll"), ("election", "Structured Election")])
    visibility = SelectField("Visibility", choices=[("public", "Public"), ("private", "Private")])
    start_time = DateTimeLocalField("Start Time", validators=[DataRequired()], format="%Y-%m-%dT%H:%M")
    expiry_time = DateTimeLocalField("Expiry Time", validators=[DataRequired()], format="%Y-%m-%dT%H:%M")
    submit = SubmitField("Create Poll")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.start_time.data:
            self.start_time.data = datetime.now()
        if not self.expiry_time.data:
            self.expiry_time.data = datetime.now() + timedelta(days=7)


class VoteForm(FlaskForm):
    option_id = HiddenField("Option", validators=[DataRequired()])
    submit = SubmitField("Cast Vote")
