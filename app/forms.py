from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField,PasswordField,SubmitField,BooleanField, TextAreaField,SelectField
from wtforms.validators import DataRequired,Length,Email,EqualTo,ValidationError
from app.models import Categories, Subscribers, Users

class RegistrationForm(FlaskForm):
    username = StringField('Username',
    validators=[DataRequired(),Length(min=2,max=20)])
    email = StringField('Email', validators=[DataRequired(),Email()])
    phone = StringField('Phone number',validators=[DataRequired()])
    password = PasswordField('Password',validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
    validators = [DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self,username):
        user = Users.query.filter_by(username = username.data).first()
        if user:
            raise ValidationError('That username is taken!')

    def validate_email(self,email):
        user = Users.query.filter_by(email = email.data).first()
        if user:
            raise ValidationError('That email is taken!')



class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(),Email()])
    password = PasswordField('Password',validators=[DataRequired()])
    remember = BooleanField('Remember me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
    validators=[DataRequired(),Length(min=2,max=20)])
    email = StringField('Email', validators=[DataRequired(),Email()])
    picture = FileField('Update profile picture', validators=[FileAllowed(['jpg','png','jpeg'])])
    submit = SubmitField('Update')

    def validate_username(self,username):
        if username.data != current_user.username:
            user = Users.query.filter_by(username = username.data).first()
            if user:
                raise ValidationError('That username is taken!')

    def validate_email(self,email):
        if email.data != current_user.email:
            user = Users.query.filter_by(email = email.data).first()
            if user:
                raise ValidationError('That email is taken!')

class PostJobForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired(),Length(min=5,max=150)])
    category = SelectField(u'Category', choices=[], validators=[DataRequired()])
    schedule = SelectField(u'Job schedule', choices=[], validators=[DataRequired()])
    location = SelectField(u'Job location', choices=[], validators=[DataRequired()])
    responsibilities = TextAreaField('Job Responsibilities', validators=[DataRequired()])
    education = StringField('Education level (Optional)', default='No education required')
    experience = StringField('Experience Requirements(Optional)', default='No experience required')
    compensation = StringField('Compensation & Other Benefits(Optional)', default='None')
    additionalreq = StringField('Additional requirements(Optional)', default='None')
    salary = StringField('Salary e.g Negotiable, Kshs.5000-Kshs.6000 or fixed price Kshs.10,000', validators=[DataRequired()])
    submit = SubmitField('Post')

class ProposalForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name', validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email', validators=[Email()])
    message = TextAreaField('Message to the recruiter', validators=[DataRequired()])
    submit = SubmitField('Submit')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(),Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self,email):
        user = Users.query.filter_by(email = email.data).first()
        if user is None:
            raise ValidationError('Email does not exist!')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('password',validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
    validators = [DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class SubscribeForm(FlaskForm):
    email = StringField('Your Email', validators=[DataRequired(),Email()])
    submit = SubmitField('Subscribe')

    def validate_email(self,email):
        user = Subscribers.query.filter_by(email = email.data).first()
        if user:
            raise ValidationError('That email is already subscribed to our newsletters!')


class ContactForm(FlaskForm):
    email = StringField('Your email', validators=[DataRequired(),Email()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')


class SendNotificationsForm(FlaskForm):
    email = StringField('Recipient email', validators=[DataRequired(),Email()])
    notification = TextAreaField('Notification message', validators=[DataRequired()])
    submit = SubmitField('Send')

    def validate_email(self,email):
        user = Users.query.filter_by(email = email.data).first()
        if user is None:
            raise ValidationError('Email does not exist!')

    
