from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import User, Job, Application, initialize_database
from file_upload import save_uploaded_file
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit

# Initialize database
initialize_database()

# Custom filter for datetime formatting
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ""
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime(format)

@app.route('/')
def index():
    jobs = Job.get_all()
    return render_template('index.html', jobs=jobs[:3])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        
        if User.get_by_username(username):
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        user_id = User.create(username, email, password, user_type)
        if user_id:
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.get_by_username(username)
        if user and user.verify_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_type'] = user.user_type
            flash('Login successful', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/jobs')
def job_list():
    jobs = Job.get_all()
    return render_template('job_list.html', jobs=jobs)

@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    job = Job.get_by_id(job_id)
    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('job_list'))
    
    has_applied = False
    application_status = None
    
    if 'user_id' in session:
        if session['user_type'] == 'job_seeker':
            applications = Application.get_by_user(session['user_id'])
            for app in applications:
                if app['job_id'] == job_id:
                    has_applied = True
                    application_status = app['status']
                    break
        
        elif session['user_type'] == 'employer' and job.posted_by == session['user_id']:
            applications = Application.get_by_job(job_id)
            return render_template('job_detail.html', 
                                job=job, 
                                has_applied=has_applied,
                                applications=applications,
                                application_status=application_status)
    
    return render_template('job_detail.html', 
                         job=job, 
                         has_applied=has_applied,
                         application_status=application_status)

@app.route('/jobs/post', methods=['GET', 'POST'])
def post_job():
    if 'user_id' not in session or session['user_type'] != 'employer':
        flash('You need to be logged in as an employer to post jobs', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        company = request.form['company']
        location = request.form['location']
        salary = request.form['salary']
        
        job_id = Job.create(title, description, company, location, salary, session['user_id'])
        if job_id:
            flash('Job posted successfully', 'success')
            return redirect(url_for('job_detail', job_id=job_id))
        else:
            flash('Failed to post job', 'error')
    
    return render_template('post_job.html')

@app.route('/jobs/<int:job_id>/apply', methods=['POST'])
def apply_job(job_id):
    if 'user_id' not in session or session['user_type'] != 'job_seeker':
        flash('You need to be logged in as a job seeker to apply', 'error')
        return redirect(url_for('login'))
    
    job = Job.get_by_id(job_id)
    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('job_list'))
    
    # Check if already applied
    applications = Application.get_by_user(session['user_id'])
    if any(app['job_id'] == job_id for app in applications):
        flash('You have already applied for this job', 'warning')
        return redirect(url_for('job_detail', job_id=job_id))
    
    # Handle file upload
    cv_file = request.files.get('cv')
    cv_filename = save_uploaded_file(cv_file) if cv_file else None
    if not cv_filename:
        flash('Please upload a valid CV (PDF, DOC, DOCX)', 'error')
        return redirect(url_for('job_detail', job_id=job_id))
    
    cover_letter = request.form.get('cover_letter', '')
    
    # Save application
    application_id = Application.create(job_id, session['user_id'], cover_letter, cv_filename)
    if application_id:
        flash('Application submitted successfully', 'success')
    else:
        flash('Failed to submit application', 'error')
    
    return redirect(url_for('job_detail', job_id=job_id))

@app.route('/my-jobs')
def my_jobs():
    if 'user_id' not in session:
        flash('Please login to view your jobs', 'error')
        return redirect(url_for('login'))
    
    user = User.get_by_id(session['user_id'])
    
    if user.user_type == 'employer':
        jobs = Job.get_by_employer(user.id)
        return render_template('my_jobs.html', 
                            jobs=jobs, 
                            is_employer=True)
    else:
        applications = Application.get_by_user(user.id)
        return render_template('my_jobs.html',
                            applications=applications,
                            is_employer=False)

@app.route('/applications/<int:app_id>/cv')
def view_cv(app_id):
    if 'user_id' not in session or session['user_type'] != 'employer':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    application = Application.get_by_id(app_id)
    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('index'))
    
    # Verify the employer owns the job
    job = Job.get_by_id(application['job_id'])
    if job.posted_by != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if not application['cv_filename']:
        flash('No CV uploaded for this application', 'error')
        return redirect(url_for('job_detail', job_id=job.id))
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        application['cv_filename'],
        as_attachment=True
    )

@app.route('/applications/<int:app_id>/update-status', methods=['POST'])
def update_application_status(app_id):
    if 'user_id' not in session or session['user_type'] != 'employer':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    application = Application.get_by_id(app_id)
    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('index'))
    
    # Verify the employer owns the job
    job = Job.get_by_id(application['job_id'])
    if job.posted_by != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    new_status = request.form.get('status')
    if new_status not in ['pending', 'reviewed', 'accepted', 'rejected']:
        flash('Invalid status', 'error')
        return redirect(url_for('job_detail', job_id=job.id))
    
    if Application.update_status(app_id, new_status):
        flash('Application status updated', 'success')
    else:
        flash('Failed to update status', 'error')
    
    return redirect(url_for('job_detail', job_id=job.id))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)