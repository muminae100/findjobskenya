import timeago,datetime
import os
import secrets
from PIL import Image
from flask import render_template,redirect,request,url_for,flash,abort,send_from_directory
from app import app,db,bcrypt,mail
from app.models import (Jobalerts, Jobs, Notifications, Proposals, Products, Productalerts,
Users, Categories, Jobschedule, Counties, Docs, Productcategories, Productimg)
from flask_login import login_user,current_user,logout_user,login_required
from app.forms import (RegistrationForm,LoginForm,UpdateAccountForm,
PostJobForm,RequestResetForm,ResetPasswordForm,ProposalForm, PostProductForm)
from flask_mail import Message
from werkzeug.utils import secure_filename
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/proposals/doc_uploads')
PRODUCTS_IMAGES_FOLDER = os.path.join(app.root_path, 'static/img/marketplace')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PRODUCTS_IMAGES_FOLDER'] = PRODUCTS_IMAGES_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    schedule = request.args.get('schedule', 'Full-time', type=str)
    category = request.args.get('category', 'House help', type=str)
    county = request.args.get('county', 'Nairobi', type=str)
    all_categories = Categories.query.all()
    categories = Categories.query.limit(10).all()
    more_categories = Categories.query.offset(10).all()
    total_categories = len(categories) + len(more_categories)
    counties = Counties.query.all()
    schedules = Jobschedule.query.all()

    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
            

    jobcategory = Categories.query.filter_by(categoryname=category).first_or_404()
    jobschedule = Jobschedule.query.filter_by(schedulename=schedule).first_or_404()
    location = Counties.query.filter_by(name=county).first_or_404()
    jobs = Jobs.query.filter_by(schedule=jobschedule).filter_by(location=location).filter_by(category=jobcategory).order_by(Jobs.date_posted.desc()).paginate(per_page=20, page=page)
    j = jobs.query.filter_by(active=True).all()
    jobs_length = len(j)
    message =  f'Showing {category} {schedule} jobs in {county}'
    return render_template('jobs/index.html', categories=categories, jobs=jobs, schedules=schedules,counties=counties,
    category=jobcategory,jobschedule=jobschedule,county=location,message=message, length = length,more_categories=more_categories,
    total_categories=total_categories,jobs_length=jobs_length,all_categories=all_categories)

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
        i = None
        f = None
        t = None
        if form.instagram.data:
            i = form.instagram.data
        if form.facebook.data:
            f = form.facebook.data
        if form.twitter.data:
            t = form.twitter.data
        newuser = Users(email=form.email.data,phone_number=form.phone.data,username=form.username.data,
        password=hashed_password,instagram=i,facebook=f,twitter=t)
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
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.profile_pic = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.phone_number = form.phone.data
        i = None
        f = None
        t = None
        if form.instagram.data:
            i = form.instagram.data
        if form.facebook.data:
            f = form.facebook.data
        if form.twitter.data:
            t = form.twitter.data
        current_user.instagram = i
        current_user.facebook = f
        current_user.twitter = t
        db.session.commit()
        flash('Account info has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.phone.data = current_user.phone_number
        form.instagram.data = current_user.instagram
        form.facebook.data = current_user.facebook
        form.twitter.data = current_user.twitter
    image_file = url_for('static', filename = 'img/profile-imgs/' + current_user.profile_pic)
    return render_template('account.html', title = current_user.username, profile_pic = image_file, form = form, length=length)

@app.route('/logout')
def logout():
    flash('You have successfully logged out','success')
    logout_user()
    return redirect(url_for('login'))

def send_alert_email(job, alert):
    msg = Message(f'{job.title}', 
                   sender='smuminaetx100@gmail.com',
                   recipients=[alert.email])
    msg.body = f'''
    A new job has been posted:

    Job title:
    {job.title}

    Job category:
    {job.category.categoryname}

    Location:
    {job.location.name}

    Job schedule:
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

    Date posted:
    {job.date_posted}

    Posted by 
    {job.author.username}

    Contact details:
    {job.author.email}
    {job.author.phone_number}

    You can view the job in our website using the link below:
    {url_for('job',id=job.id,_external = True)}

    Click the link below to unsubscribe from this job alert
    {url_for('unsubscribe_job',id=alert.id,_external = True)}

'''
    mail.send(msg)


def send_notification(j, receiver):
    s = Users.query.filter_by(email=j.author.email).first_or_404()
    r = Users.query.filter_by(email=receiver).first_or_404()
    message = f'''
    <h6>A new job has been posted:</h6>
    <div>
    <a class="text-primary" href="{url_for('job',id=j.id)}">
    {j.title}
    </a>
    </div>
    
    '''
    
    notification = Notifications(sender=s.email, receiver=r.email, message=message)
    db.session.add(notification)
    db.session.commit()

def check_alerts(j):
    alerts = Jobalerts.query.filter_by(category=j.category.categoryname).filter_by(county=j.location.name).filter_by(schedule=j.schedule.schedulename).all()
    if alerts:
        for alert in alerts:
            send_alert_email(j, alert)
            send_notification(j, alert.email)



# jobs
@app.route('/postnewjob', methods = ['GET', 'POST'])
@login_required
def newjob():
    form =PostJobForm()
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
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
        j = Jobs.query.order_by(Jobs.id.desc()).first_or_404()
        check_alerts(j)
        flash('Your job has been posted successfully!', 'success')
        return redirect(url_for('job',id=job.id))
    return render_template('jobs/newjob.html', title = 'Post new job',form=form, text = 'Post a New Job', length=length)


@app.route('/job/<int:id>', methods = ['GET', 'POST'])
def job(id):
    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
    form =ProposalForm()
    job = Jobs.query.get_or_404(int(id))
    now = datetime.datetime.now() 
    time_posted = timeago.format(job.date_posted, now)
    return render_template('jobs/job-application.html', title=job.title, job = job,time_posted=time_posted,form=form, length=length)

@app.route('/job/<int:id>/update', methods = ['GET', 'POST'])
@login_required
def jobupdate(id):
    job = Jobs.query.get_or_404(int(id))
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
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

    return render_template('jobs/updatejob.html', title = 'Update job post', form = form, text = 'Update post', length=length)


@app.route('/job/<int:id>/delete', methods = ['POST'])
@login_required
def deletejob(id):
    job = Jobs.query.get_or_404(id)
    if job.author != current_user:
        abort(404)

    db.session.delete(job)
    db.session.commit()
    flash('Your job post has been deleted!', 'success')
    return redirect(url_for('author_jobs', username= current_user.username ))

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
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
    user = Users.query.filter_by(username=username).first_or_404()
    j = []
    jobs = Jobs.query.filter_by(author=user)\
        .order_by(Jobs.date_posted.desc())\
        .all()
    for job in jobs:
        j.append(job)
    length_of_jobs = len(j)
    return render_template('jobs/user-jobs.html',jobs = jobs, length=length,length_of_jobs=length_of_jobs)


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


@app.route('/terms_of_use')
def terms_conditions():
    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
    return render_template('terms_of_use.html', title='Terms of use', length=length)

@app.route('/contact_us')
def contact_us():
    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
    return render_template('contact.html', title='Contact Us', length=length)

@app.route('/safety_tips')
def safety_tips():
    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
    return render_template('safety-tips.html', title='Stay safe on ForeverKenyan', length=length)

@app.route('/faq')
def faq():
    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
    return render_template('faq.html', title='FAQ', length=length)

@app.route('/privacy_policy')
def privacy_policy():
    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
    return render_template('privacy_policy.html', title='Privacy policy',length=length)



# save job

@app.route('/savejob/<int:id>')
@login_required
def save_job(id):
    job = Jobs.query.get_or_404(int(id))
    if job.author == current_user:
        flash('You can not save your own job', 'danger')
    current_user.saved_jobs.append(job)
    db.session.commit()
    flash('Job saved successfully', 'success')
    return redirect(url_for('saved_jobs'))

@app.route('/saved_jobs')
@login_required
def saved_jobs():
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)

    j = []
    jobs = current_user.saved_jobs
    for job in jobs:
        j.append(job)
    length_of_jobs = len(j)
    return render_template('jobs/saved-jobs.html', jobs=jobs, length=length,length_of_jobs=length_of_jobs)




# proposals

def send_email_applicant(proposal, job, m):
    msg = Message(f'You have received a reply from {job.author.username}', 
                   sender= f'smuminaetx100@gmail.com',
                   recipients=[proposal.job_seeker.email])
    msg.body = f'''
    Message:
    {m}

    This message was send after you had applied for the job below:
    View job: {url_for('job',id=job.id,_external = True)}

'''
    mail.send(msg)


def send_notification_applicant(p,j):
    s = Users.query.filter_by(email=j.author.email).first_or_404()
    r = Users.query.filter_by(email=p.job_seeker.email).first_or_404()
    message = f'''
    Your  job proposal has been submitted successfully!

    View the proposal with the link below:
    <a class="text-primary" href="{url_for('proposal', id=p.id)}">My proposal</a>

    You are applying for the job below:
    <a class="text-primary" href="{url_for('job', id=j.id)}">{j.title}</a>
    
    '''
    
    notification = Notifications(sender=s.email, receiver=r.email, message=message)
    db.session.add(notification)
    db.session.commit()


def send_email_recruiter(proposal, job):
    msg = Message(f'You have received a new job proposal from {proposal.job_seeker.username}', 
                   sender= 'smuminaetx100@gmail.com',
                   recipients=[job.author.email])
    msg.body = f'''
    Applicant information:
    First Name: {proposal.firstname}
    Last Name: {proposal.lastname}
    Phone Number: {proposal.phone}
    Email: {proposal.email}

    Message:
    {proposal.message}

    Application applied for your job posted below:
    view job: {url_for('job',id=job.id)}
    
    You can view all the job proposals in our website using the link below:
    {url_for('submitted_proposals',id=job.id,_external = True)}

'''
    mail.send(msg)


def send_notification_recruiter(p,j):
    s = Users.query.filter_by(email=p.job_seeker.email).first_or_404()
    r = Users.query.filter_by(email=j.author.email).first_or_404()
    message = f'''
    You have received a new job proposal from {p.job_seeker.username}

    Applicant information:
    First Name: {p.firstname}
    Last Name: {p.lastname}
    Phone Number: {p.phone}
    Email: {p.email}

    Message:
    {p.message}

    Applicant applying for the job you posted below:
    View job: {url_for('job',id-j.id)}
    '''
    
    notification = Notifications(sender=s.email, receiver=r.email, message=message)
    db.session.add(notification)
    db.session.commit()



def send_proposal_emails(p, j):
    send_email_recruiter(p, j)
    send_notification_applicant(p, j)
    send_notification_recruiter(p, j)

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

        send_proposal_emails(proposal, job)

        flash('Job proposal submitted successfully', 'success')
    return redirect(url_for('my_proposals'))

@app.route('/my-proposals')
@login_required
def my_proposals():
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
    return render_template('jobs/proposals.html', length=length)




def send_doc_recruiter(proposal, job, doc):
    msg = Message(f'{proposal.job_seeker.username} has uploaded a new document to add on to his/her job application', 
                   sender= 'smuminaetx100@gmail.com',
                   recipients=[job.author.email])
    msg.body = f'''
    Document uploaded: 

    {url_for('uploaded_file',filename={doc.docname},_external = True)}
    Uploaded on {doc.date_uploaded}

    Applicant information:
    First Name: {proposal.firstname}
    Last Name: {proposal.lastname}
    Phone Number: {proposal.phone}
    Email: {proposal.email}

    Message:
    {proposal.message}

    Job applied for:

    {url_for('job',id=job.id,_external = True)}

    All applications link:

    {url_for('submitted_proposals',id=job.id,_external = True)}

'''
    mail.send(msg)


def send_doc_recruiter_notification(proposal,job,doc):
    s = Users.query.filter_by(email=proposal.job_seeker.email).first_or_404()
    r = Users.query.filter_by(email=job.author.email).first_or_404()
    message = f'''
    {proposal.job_seeker.username} has uploaded a new document to add on to his/her job application

    Document uploaded: 

    {url_for('uploaded_file',filename={doc.docname},_external = True)}
    Uploaded on {doc.date_uploaded}

    Applicant information:
    First Name: {proposal.firstname}
    Last Name: {proposal.lastname}
    Phone Number: {proposal.phone}
    Email: {proposal.email}

    Message:
    {proposal.message}

    Job applied for:

    {url_for('job',id=job.id,_external = True)}

    All applications link:

    {url_for('submitted_proposals',id=job.id,_external = True)}

    '''
    
    notification = Notifications(sender=s.email, receiver=r.email, message=message)
    db.session.add(notification)
    db.session.commit()

@app.route('/proposal/<int:id>', methods=['GET', 'POST'])
@login_required
def proposal(id):
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
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

            send_doc_recruiter(proposal, proposal.its_job, doc)
            send_doc_recruiter_notification(proposal, proposal.its_job, doc)

            return fn

    return render_template('jobs/proposal.html', proposal=proposal, length=length)

@app.route('/update-proposal/<int:id>', methods=['GET', 'POST'])
@login_required
def update_proposal(id):
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
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
    return render_template('jobs/update-proposal.html', form=form, proposal=proposal, length=length)

@app.route('/delete-doc/<string:docname>/<int:id>')
@login_required
def deletedoc(docname, id):
    doc = Docs.query.filter_by(docname=docname).first_or_404()
    if doc.uploader != current_user:
        abort(404)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], doc.docname))
    db.session.delete(doc)
    db.session.commit()
    return redirect(url_for('proposal', id= id))

@app.route('/delete-proposal/<int:id>', methods = ['POST'])
@login_required
def delete_proposal(id):
    proposal = Proposals.query.get_or_404(int(id))
    if proposal.job_seeker != current_user:
        abort(404)
    for doc in proposal.docs:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], doc.docname))

    db.session.delete(proposal)
    db.session.commit()
    flash('Your job proposal has been deleted successfully!', 'success')
    return redirect(url_for('my_proposals'))

@app.route('/proposals_for_job/<int:id>')
@login_required
def submitted_proposals(id):
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
    job = Jobs.query.get_or_404(int(id))
    if job.author != current_user:
        abort(404)
   
    flash(f'Showing proposals for {job.title}!', 'secondary')
    return render_template('jobs/submitted-proposals.html', job=job, length=length)

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

    alert = Jobalerts(email=email, category=c.categoryname, schedule=s.schedulename,county=l.name)
    db.session.add(alert)
    db.session.commit()

    flash(f'You job alert has been set successfully', 'secondary')

    return redirect(url_for('index'))

@app.route('/notifications')
@login_required
def notifications():
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    l = []

    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            l.append(notification)

    for notification in notifications:
        if notification.receiver == current_user.email:
            notification.read = True
            db.session.commit()


    length = len(l)
    return render_template('notifications.html', notifications=l, length=length)



def send_applicant_reply(p,j,m):
    s = Users.query.filter_by(email=j.author.email).first_or_404()
    r = Users.query.filter_by(email=p.job_seeker.email).first_or_404()
    message = f'''
    You have received a reply from {j.author.username}
    
    Message:
    {m}

    This message is a reply from a recruiter after you had applied for the job below:
    {url_for('job', id=j.id)}
    
    '''
    
    notification = Notifications(sender=s.email, receiver=r.email, message=message)
    db.session.add(notification)
    db.session.commit()

@app.route('/send_msg_applicant/<int:j_id>/<int:p_id>', methods = ['POST'])
@login_required
def send_msg_applicant(j_id, p_id):
    msg = request.form.get('msg')
    p = Proposals.query.get(int(p_id))
    j = Jobs.query.get(int(j_id))
    if j.author != current_user:
        abort(404)
    send_email_applicant(p, j, msg)
    send_applicant_reply(p, j, msg)

    flash('You have successfully sent the message to the applicant', 'success')
    return redirect(url_for('submitted_proposals', id=j.id))


# market place
@app.route('/marketplace')
def market_place():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', 'Electronics', type=str)
    county = request.args.get('county', 'Nairobi', type=str)
    all_categories = Productcategories.query.all()
    categories = Productcategories.query.limit(10).all()
    more_categories = Productcategories.query.offset(10).all()
    total_categories = len(categories) + len(more_categories)
    counties = Counties.query.all()

    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
            

    productcategory = Productcategories.query.filter_by(productcategoryname=category).first_or_404()
    location = Counties.query.filter_by(name=county).first_or_404()
    products = Products.query.filter_by(product_location=location).filter_by(product_category=productcategory).order_by(Products.date_posted.desc()).paginate(per_page=20, page=page)
    message =  f'Showing {category} products in {county}'
    return render_template('marketplace/index.html', categories=categories, products=products,counties=counties,
    category=productcategory,county=location,message=message, length = length,more_categories=more_categories,
    total_categories=total_categories,all_categories=all_categories)


def send_product_alert_email(product, alert):
    msg = Message(f'{product.title}', 
                   sender='smuminaetx100@gmail.com',
                   recipients=[alert.email])
    msg.body = f'''
    A new product/service has been posted:

    {product.title}

    Category:
    {product.product_category.productcategoryname}

    Location:
    {product.product_location.name}

    {product.additional_details}

    Price:
    {product.price}

    Date posted:
    {product.date_posted}

    Posted by 
    {product.owner.username}

    Contact details:
    {product.owner.email}
    {product.owner.phone_number}

    You can view the product/service in our website using the link below:
    {url_for('product',id=product.id,_external = True)}

    Click the link below to unsubscribe from this alert
    {url_for('unsubscribe_product',id=alert.id,_external = True)}

'''
    mail.send(msg)


def send_product_notification(p, receiver):
    s = Users.query.filter_by(email=p.owner.email).first_or_404()
    r = Users.query.filter_by(email=receiver).first_or_404()
    message = f'''
    <h6>A new product/service has been posted:</h6>
    <p><b>View:</b></p>
    <a class="text-primary" href="{url_for('product',id=p.id)}">{p.title}</a>
   
    '''
    
    notification = Notifications(sender=s.email, receiver=r.email, message=message)
    db.session.add(notification)
    db.session.commit()

def check_product_alerts(p):
    alerts = Productalerts.query.filter_by(category=p.product_category.productcategoryname).filter_by(county=p.product_location.name).all()
    if alerts:
        for alert in alerts:
            send_product_alert_email(p, alert)
            send_product_notification(p, alert.email)


@app.route('/create_alert', methods = ['POST'])
@login_required
def product_alert():
    category = request.form.get('category')
    county = request.form.get('county')
    c = Productcategories.query.filter_by(productcategoryname=category).first_or_404()
    l = Counties.query.filter_by(name=county).first_or_404()
    email = current_user.email

    alert = Productalerts(email=email, category=c.productcategoryname,county=l.name)
    db.session.add(alert)
    db.session.commit()

    flash(f'Your alert has been set successfully', 'info')

    return redirect(url_for('market_place'))

@app.route('/postnewproduct', methods = ['GET', 'POST'])
@login_required
def newproduct():
    form =PostProductForm()
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
    form.category.choices = [(category.id, category.productcategoryname) for category in Productcategories.query.all()]
    form.location.choices = [(location.id, location.name) for location in Counties.query.all()]
    if form.validate_on_submit():
        product = Products(title=form.title.data,category_id=form.category.data,
        owner=current_user,location_id=form.location.data,
        price=form.price.data,additional_details=form.additionaldetails.data,
        )
        db.session.add(product)
        db.session.commit()
        p = Products.query.order_by(Products.id.desc()).first_or_404()
        check_product_alerts(p)
        flash('Add images to your product/service.', 'info')
        return redirect(url_for('addproductimgs',id=product.id))
    return render_template('marketplace/new-product.html', title = 'Post new product/service',form=form, text = 'Post a New Product/Service', length=length)


@app.route('/add-product-images/<int:id>', methods=['GET', 'POST'])
@login_required
def addproductimgs(id):
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)

    product = Products.query.get_or_404(int(id))
    if product.owner != current_user:
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
            file.save(os.path.join(app.config['PRODUCTS_IMAGES_FOLDER']  , fn))


            product = Products.query.get_or_404(int(id))
            image = Productimg(name=fn,product=product)
            db.session.add(image)
            db.session.commit()

            return fn

    return render_template('marketplace/add-images.html', product=product, length=length)


@app.route('/product/<int:id>', methods = ['GET', 'POST'])
def product(id):
    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
    product = Products.query.get_or_404(int(id))
    images = []
    imgs = product.images
    for img in imgs:
        images.append(img)
    length_of_imgs = len(images)
    if product.owner == current_user and length_of_imgs == 0:
        flash('Product/service must have at least one image!', 'info')
        return redirect(url_for('addproductimgs', id= product.id))
    now = datetime.datetime.now() 
    time_posted = timeago.format(product.date_posted, now)
    return render_template('marketplace/product.html', title=product.title, product = product,
    time_posted=time_posted, length=length, length_of_imgs=length_of_imgs, imgs=imgs)

@app.route('/product/<int:id>/update', methods = ['GET', 'POST'])
@login_required
def productupdate(id):
    product = Products.query.get_or_404(int(id))
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
    if product.owner != current_user:
        abort(404)

    form = PostProductForm()
    form.category.choices = [(category.id, category.productcategoryname) for category in Productcategories.query.all()]
    form.location.choices = [(location.id, location.name) for location in Counties.query.all()]
    if form.validate_on_submit():
        product.title = form.title.data
        product.category_id = form.category.data
        product.location_id = form.location.data
        product.additional_details = form.additionaldetails.data
        product.price = form.price.data
        db.session.commit()
        flash('Your product/service post has been updated!', 'success')
        return redirect(url_for('addproductimgs',id = product.id))
    elif request.method == 'GET':
        form.title.data = product.title
        form.category.data = product.category_id
        form.location.data = product.location_id
        form.additionaldetails.data = product.additional_details
        form.price.data = product.price

    return render_template('marketplace/updateproduct.html', title = 'Update product post', form = form, text = 'Update product', length=length)


@app.route('/product/<int:id>/delete', methods = ['POST'])
@login_required
def deleteproduct(id):
    product = Products.query.get_or_404(id)
    if product.owner != current_user:
        abort(404)

    for img in product.images:
        os.remove(os.path.join(app.config['PRODUCTS_IMAGES_FOLDER'], img.name))
        db.session.delete(img)
        db.session.commit()

    db.session.delete(product)
    db.session.commit()
    flash('Your product/service post has been deleted!', 'success')
    return redirect(url_for('author_products'))


@app.route('/delete-image/<string:imgname>/<int:id>')
@login_required
def deleteimg(imgname, id):
    img = Productimg.query.filter_by(name=imgname).first_or_404()
    product = Products.query.get(int(id))
    if product.owner != current_user:
        abort(404)
    os.remove(os.path.join(app.config['PRODUCTS_IMAGES_FOLDER'], img.name))
    db.session.delete(img)
    db.session.commit()
    return redirect(url_for('addproductimgs', id= id))

@app.route('/my-products')
@login_required
def author_products():
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
    return render_template('marketplace/author_products.html', length=length)


# save product

@app.route('/addfavourite/<int:id>')
@login_required
def save_product(id):
    product = Products.query.get_or_404(int(id))
    if product.owner == current_user:
        flash('You can not like your own product', 'danger')
        return redirect(url_for('market_place'))
    if product in current_user.saved_products:
        flash('You already liked this product', 'info')
        return redirect(url_for('market_place'))
    current_user.saved_products.append(product)
    db.session.commit()
    flash('Product/service added to your favourites', 'success')
    return redirect(url_for('market_place'))

@app.route('/favourite-products')
@login_required
def saved_products():
    n = []
    notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
    for notification in notifications:
        if notification.receiver == current_user.email and notification.read == False:
            n.append(notification)

    length = len(n)
    products = current_user.saved_products
    return render_template('marketplace/saved-products.html', products=products, length=length)

# unsubscribe emails
@app.route('/unsubscribe_jobalert/<int:id>')
def unsubscribe_job(id):
    alert = Jobalerts.query.get_or_404(int(id))
    db.session.delete(alert)
    db.session.commit()
    flash('You have successfully unsubscribed from job alert')
    return redirect(url_for('index'))

@app.route('/unsubscribe_productalert/<int:id>')
def unsubscribe_product(id):
    alert = Productalerts.query.get_or_404(int(id))
    db.session.delete(alert)
    db.session.commit()
    flash('You have successfully unsubscribed from product/service alert')
    return redirect(url_for('market_place'))


#handling errors
@app.errorhandler(404)
def page_not_found(e):
    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
    return render_template('404.html', length=length), 404

@app.errorhandler(500)
def internal_error(error):
    length = 0

    if current_user.is_authenticated:
        n = []
        notifications = Notifications.query.order_by(Notifications.date_sent.desc()).all()
        for notification in notifications:
            if notification.receiver == current_user.email and notification.read == False:
                n.append(notification)

        length = len(n)
    return render_template('500.html', length=length), 500




# admin
@app.route('/add_category', methods = ['POST'])
@login_required
def add_category():
    if current_user.admin != True:
        abort(404)
    category = request.form.get('category')
    c = Categories(categoryname=category)
    db.session.add(c)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/del_category/<int:id>', methods = ['POST'])
@login_required
def del_category(id):
    if current_user.admin != True:
        abort(404)
    c = Categories.query.get_or_404(int(id))
    db.session.delete(c)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/addnewcategory', methods = ['POST'])
@login_required
def add_productcategory():
    if current_user.admin != True:
        abort(404)
    category = request.form.get('category')
    c = Productcategories(productcategoryname=category)
    db.session.add(c)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/del_productcategory/<int:id>', methods = ['POST'])
@login_required
def del_productcategory(id):
    if current_user.admin != True:
        abort(404)
    c = Productcategories.query.get_or_404(int(id))
    db.session.delete(c)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/del_user/<int:id>', methods = ['POST'])
@login_required
def del_user(id):
    if current_user.admin != True:
        abort(404)
    u = Users.query.get_or_404(int(id))
    db.session.delete(u)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/del_job/<int:id>', methods = ['POST'])
@login_required
def del_job(id):
    if current_user.admin != True:
        abort(404)
    j = Jobs.query.get_or_404(int(id))
    db.session.delete(j)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/del_product/<int:id>', methods = ['POST'])
@login_required
def del_product(id):
    if current_user.admin != True:
        abort(404)
    p = Products.query.get_or_404(int(id))
    db.session.delete(p)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin')
@login_required
def admin():
    if current_user.admin != True:
        abort(404)
    users = Users.query.paginate()
    categories = Categories.query.paginate()
    jobs = Jobs.query.paginate()
    products = Products.query.paginate()
    marketplace_cat = Productcategories.query.paginate()

    return render_template('admin/index.html', users=users,categories=categories,
    marketplace_cat=marketplace_cat, jobs=jobs,products=products)