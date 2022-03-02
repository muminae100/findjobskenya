import timeago,datetime
import os
import secrets
from PIL import Image
from flask import render_template,redirect,request,url_for,flash,abort,jsonify,send_from_directory
from app import app,db,bcrypt,mail
from app.models import Jobalerts, Jobs, Proposals, Users, Categories, Jobschedule, Counties, Docs
from flask_login import login_user,current_user,logout_user,login_required
from app.forms import (RegistrationForm,LoginForm,UpdateAccountForm,
PostJobForm,RequestResetForm,ResetPasswordForm,ContactForm,SubscribeForm,ProposalForm)
from flask_mail import Message
from werkzeug.utils import secure_filename
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/proposals/doc_uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)


@app.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    schedule = request.args.get('schedule', 'Full-time', type=str)
    category = request.args.get('category', 'House help', type=str)
    county = request.args.get('county', 'Nairobi', type=str)
    categories = Categories.query.paginate()
    counties = Counties.query.all()
    schedules = Jobschedule.query.all()
    jobcategory = Categories.query.filter_by(categoryname=category).first_or_404()
    jobschedule = Jobschedule.query.filter_by(schedulename=schedule).first_or_404()
    location = Counties.query.filter_by(name=county).first_or_404()
    jobs = Jobs.query.filter_by(schedule=jobschedule).filter_by(location=location).filter_by(category=jobcategory).order_by(Jobs.date_posted.desc()).paginate(per_page=20, page=page)
    message =  f'Showing {category} {schedule} jobs in {county}'
    return render_template('index.html', categories=categories, jobs=jobs, schedules=schedules,counties=counties,
    category=jobcategory,jobschedule=jobschedule,county=location,message=message)

@app.route('/login', methods = ['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email = form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember = form.remember.data)
            flash('You have been successfully logged in!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Email or password incorrect!','danger')
    return render_template('login.html', title = 'Login', form = form)

@app.route('/register', methods = ['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        newuser = Users(email=form.email.data,phone_number=form.phone.data,username=form.username.data,password=hashed_password)
        db.session.add(newuser)
        db.session.commit()

        flash('Registered successfully! Login to access your account.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title = 'Register', form = form)

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _,f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/img/profile-imgs', picture_fn)

    output_size = (250, 250)
    i = Image.open(form_picture)
    i.thumbnail(output_size)

    i.save(picture_path)
    return picture_fn    

@app.route('/account', methods = ['GET','POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.profile_pic = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Account info has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename = 'img/profile-imgs/' + current_user.profile_pic)
    return render_template('account.html', title = current_user.username, profile_pic = image_file, form = form)

# @app.route('/subscribe', methods = ['GET','POST'])
# def subscribe():
#     form = SubscribeForm()
#     if form.validate_on_submit():
#         subscriber = Subscribers(email=form.email.data)
#         db.session.add(subscriber)
#         db.session.commit()
#         flash('You have successfully subscribed to our newsletter', 'success')
#         return redirect(url_for('index'))
#     return render_template('subscribe.html',form=form)

@app.route('/logout')
def logout():
    flash('You have successfully logged out','success')
    logout_user()
    return redirect(url_for('login'))

def send_alert_email(job, user):
    msg = Message('Job alert', 
                   sender='smuminaetx100@gmail.com',
                   recipients=[user.email])
    msg.body = f'''A new job has been posted:

{job.title}
{job.category.categoryname}
{job.location.name}
{job.schedule.schedulename}
Job responsibilities:
{job.job_responsibilities}
Education level:
{job.education}
Experience:
{job.experience}
Additional requirements:
{job.additional_req}
Compensation:
{job.compensation}
Job Active:
{job.active}
Salary:
{job.salary}
{job.date_posted}
Posted by 
{job.author.username}
Contact details:
{job.author.email}
{job.author.phone_number}

You can view the job in our website using the link below:
{url_for('job',id={job.id},_external = True)}

'''
    mail.send(msg)

def check_alerts(j):
    alert = Jobalerts.query.filter_by(category=j.category).filter_by(county=j.county).filter_by(schedule=j.schedule).all()
    if alert:
        send_alert_email(j, alert.email)


# jobs
@app.route('/postnewjob', methods = ['GET', 'POST'])
@login_required
def newjob():
    form =PostJobForm()
    form.category.choices = [(category.id, category.categoryname) for category in Categories.query.all()]
    form.schedule.choices = [(schedule.id, schedule.schedulename) for schedule in Jobschedule.query.all()]
    form.location.choices = [(location.id, location.name) for location in Counties.query.all()]
    if form.validate_on_submit():
        job = Jobs(title=form.title.data,category_id=form.category.data,schedule_id=form.schedule.data,
        education=form.education.data,author=current_user,experience=form.experience.data,location_id=form.location.data,
        salary=form.salary.data,job_responsibilities=form.responsibilities.data,additional_req=form.additionalreq.data,
        compensation=form.compensation.data)
        db.session.add(job)
        db.session.commit()
        j = Jobs.query.first_or_404()
        check_alerts(j)
        flash('Your job has been posted successfully!', 'success')
        return redirect(url_for('job',id=job.id))
    return render_template('newjob.html', title = 'Post new job',form=form, text = 'Post a New Job')


@app.route('/<int:id>', methods = ['GET', 'POST'])
@login_required
def job(id):
    form =ProposalForm()
    job = Jobs.query.get_or_404(int(id))
    now = datetime.datetime.now() 
    time_posted = timeago.format(job.date_posted, now)
    return render_template('job-application.html', title=job.title, job = job,time_posted=time_posted,form=form)

@app.route('/<int:id>/update', methods = ['GET', 'POST'])
@login_required
def jobupdate(id):
    job = Jobs.query.get_or_404(int(id))
    if job.author != current_user:
        abort(404)

    form = PostJobForm()
    form.category.choices = [(category.id, category.categoryname) for category in Categories.query.all()]
    form.schedule.choices = [(schedule.id, schedule.schedulename) for schedule in Jobschedule.query.all()]
    form.location.choices = [(location.id, location.name) for location in Counties.query.all()]
    if form.validate_on_submit():
        job.title = form.title.data
        job.category_id = form.category.data
        job.schedule_id = form.schedule.data
        job.location_id = form.location.data
        job.job_responsibilities = form.responsibilities.data
        job.education = form.education.data
        job.experience = form.experience.data
        job.additional_req = form.additionalreq.data
        job.compensation = form.compensation.data
        job.salary = form.salary.data
        db.session.commit()
        flash('Your job post has been updated!', 'success')
        return redirect(url_for('job',id = job.id))
    elif request.method == 'GET':
        form.title.data = job.title
        form.category.data = job.category_id
        form.schedule.data = job.schedule_id
        form.location.data = job.location_id
        form.responsibilities.data = job.job_responsibilities
        form.education.data = job.education
        form.experience.data = job.experience
        form.additionalreq.data = job.additional_req
        form.compensation.data = job.compensation
        form.salary.data = job.salary

    return render_template('updatejob.html', title = 'Update job post', form = form, text = 'Update post')


@app.route('/<int:id>/delete', methods = ['POST'])
@login_required
def deletejob(id):
    job = Jobs.query.get_or_404(id)
    if job.author != current_user:
        abort(404)

    db.session.delete(job)
    db.session.commit()
    flash('Your job post has been deleted!', 'success')
    return redirect(url_for('index'))

@app.route('/togglejob/<int:id>/', methods = ['POST'])
@login_required
def togglejob(id):
    job = Jobs.query.get_or_404(int(id))
    if job.author != current_user:
        abort(404)
    job.active = not job.active
    db.session.commit()
    flash('Your job post has been toggled!', 'success')
    return redirect(url_for('author_jobs', username= current_user.username ))



@app.route('/author/<string:username>')
@login_required
def author_jobs(username):
    user = Users.query.filter_by(username=username).first_or_404()
    jobs = Jobs.query.filter_by(author=user)\
        .order_by(Jobs.date_posted.desc())\
        .all()
    return render_template('user-jobs.html',jobs = jobs)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', 
                   sender='smuminaetx100@gmail.com',
                   recipients=[user.email])
    msg.body = f'''To reset your password, click the link below:
{url_for('reset_token',token=token,_external = True)}
Token expires within one hour!
If you did not make this request simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route('/reset_password', methods = ['GET','POST'])
def reset_request():
    form = RequestResetForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email = form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title = 'Reset Password', form = form)

@app.route('/reset_password/<token>', methods = ['GET','POST'])
def reset_token(token):
    user = Users.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token!', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash(f'Your password has been updated! You are now able to login and access your account', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title = 'Reset Password', form = form)


@app.route('/terms_and_conditions')
def terms_conditions():
    return render_template('Terms_and_conditions.html', title='Terms and conditions')

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html', title='Privacy policy')



# save job

@app.route('/job/<int:id>')
@login_required
def save_job(id):
    job = Jobs.query.get_or_404(int(id))
    current_user.saved_jobs.append(job)
    db.session.commit()
    flash('Job saved successfully', 'success')
    return redirect(url_for('saved_jobs'))

@app.route('/saved_jobs')
@login_required
def saved_jobs():
    jobs = current_user.saved_jobs
    return render_template('saved-jobs.html', jobs=jobs)



# proposals
@app.route('/submit_proposal/job/<int:id>', methods =['POST'])
@login_required
def submit_proposal(id):
    form =ProposalForm()
    job = Jobs.query.get_or_404(int(id))
    if form.validate_on_submit():
        proposal = Proposals(firstname=form.firstname.data,lastname=form.lastname.data,phone=form.phone.data,
        email=form.email.data,message=form.message.data,job_seeker=current_user,its_job=job)
        db.session.add(proposal)
        db.session.commit()
        flash('Job proposal submitted successfully', 'success')
    return redirect(url_for('my_proposals'))

@app.route('/my-proposals')
@login_required
def my_proposals():
    return render_template('proposals.html')

@app.route('/proposal/<int:id>', methods=['GET', 'POST'])
@login_required
def proposal(id):
    proposal = Proposals.query.get_or_404(int(id))
    if proposal.job_seeker != current_user:
        abort(404)
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            random_hex = secrets.token_hex(8)
            _,f_ext = os.path.splitext(filename)
            fn = random_hex + f_ext
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))

            proposal = Proposals.query.get_or_404(int(id))
            doc = Docs(docname=fn, uploader=current_user,proposal=proposal)
            db.session.add(doc)
            db.session.commit()

            return fn

    return render_template('proposal.html', proposal=proposal)

@app.route('/update-proposal/<int:id>', methods=['GET', 'POST'])
@login_required
def update_proposal(id):
    proposal = Proposals.query.get_or_404(int(id))
    form =ProposalForm()
    if proposal.job_seeker != current_user:
        abort(404)
  
    if form.validate_on_submit():
        proposal.firstname = form.firstname.data
        proposal.lastname = form.lastname.data
        proposal.phone = form.phone.data
        proposal.email = form.email.data
        proposal.message = form.message.data

        db.session.commit()
        flash('Job proposal updated successfully', 'success')
        return redirect(url_for('proposal', id=proposal.id))
    elif request.method == 'GET':
        form.firstname.data = proposal.firstname
        form.lastname.data = proposal.lastname
        form.phone.data = proposal.phone
        form.email.data = proposal.email
        form.message.data = proposal.message
    return render_template('update-proposal.html', form=form, proposal=proposal)


@app.route('/delete-proposal/<int:id>', methods = ['POST'])
@login_required
def delete_proposal(id):
    proposal = Proposals.query.get_or_404(int(id))
    if proposal.job_seeker != current_user:
        abort(404)

    db.session.delete(proposal)
    db.session.commit()
    flash('Your job proposal has been deleted successfully!', 'success')
    return redirect(url_for('my_proposals'))

@app.route('/proposals_for_job/<int:id>')
@login_required
def submitted_proposals(id):
    job = Jobs.query.get_or_404(int(id))
    if job.author != current_user:
        abort(404)
   
    flash(f'Showing proposals for {job.title}!', 'secondary')
    return render_template('submitted-proposals.html', job=job)

@app.route('/job_alert', methods = ['POST'])
@login_required
def job_alerts():
    category = request.form.get('category')
    schedule = request.form.get('schedule')
    county = request.form.get('county')
    c = Categories.query.filter_by(categoryname=category).first_or_404()
    s = Jobschedule.query.filter_by(schedulename=schedule).first_or_404()
    l = Counties.query.filter_by(name=county).first_or_404()
    email = current_user.email

    alert = Jobalerts(email=email, category=c, schedule=s,county=l)
    db.session.add(alert)
    db.session.commit()

    flash(f'You job alert has been set successfully', 'secondary')

    return redirect(url_for('index'))