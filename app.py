from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pymysql
import re

pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------------- DATABASE ----------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Nalini%40123@localhost/student_feedback_system'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class Student(db.Model):
    __tablename__ = 'students'
    student_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    branch = db.Column(db.String(50))
    password = db.Column(db.String(50))

class Faculty(db.Model):
    __tablename__ = 'faculty'
    faculty_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    subject = db.Column(db.String(100))

class Feedback(db.Model):
    __tablename__ = 'feedback'
    feedback_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'))
    rating = db.Column(db.Integer)
    comments = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.now)

# ---------------- HELPER FUNCTION ----------------
def is_valid_sreenidhi_email(email):
    # Only allow emails ending with rollnumber@sreenidhi.edu.in
    pattern = r'^\d+@sreenidhi\.edu\.in$'
    return re.match(pattern, email)

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('index.html')

# ---------------- STUDENT REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        branch = request.form['branch']
        password = request.form['password']

        if not is_valid_sreenidhi_email(email):
            flash("Registration allowed only with rollnumber@sreenidhi.edu.in email!", "error")
            return redirect('/register')

        existing = Student.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered!", "error")
            return redirect('/register')

        new_student = Student(
            name=name,
            email=email,
            branch=branch,
            password=password
        )
        db.session.add(new_student)
        db.session.commit()
        flash("Registration Successful! Please login.", "success")
        return redirect('/login')

    return render_template('register.html')

# ---------------- STUDENT LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    forgot = request.args.get('forgot')

    if request.method == 'POST':
        if 'login' in request.form:
            email = request.form['email']
            password = request.form['password']

            if not is_valid_sreenidhi_email(email):
                flash("Login allowed only with rollnumber@sreenidhi.edu.in email!", "error")
                return redirect(url_for('login'))

            user = Student.query.filter_by(email=email, password=password).first()
            if user:
                session['student_id'] = user.student_id
                session['name'] = user.name
                flash("Logged in successfully!", "success")
                return redirect('/dashboard')

            flash("Invalid Email or Password", "error")
            return redirect(url_for('login'))

        elif 'reset' in request.form:
            email = request.form['email']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if new_password != confirm_password:
                flash("Passwords do not match!", "error")
                return redirect(url_for('login', forgot=1))

            if not is_valid_sreenidhi_email(email):
                flash("Password reset allowed only for rollnumber@sreenidhi.edu.in email!", "error")
                return redirect(url_for('login', forgot=1))

            user = Student.query.filter_by(email=email).first()
            if user:
                user.password = new_password
                db.session.commit()
                flash("Password reset successfully! Please login.", "success")
                return redirect(url_for('login'))
            else:
                flash("Email not found!", "error")
                return redirect(url_for('login', forgot=1))

    return render_template('login.html', forgot=forgot)

# ---------------- ADMIN LOGIN ----------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    feedbacks = []
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == "admin@gmail.com" and password == "admin123":
            session['admin'] = True
            flash("Admin Login Successful!", "success")
            feedbacks = db.session.query(Feedback, Faculty, Student)\
                        .join(Faculty, Feedback.faculty_id == Faculty.faculty_id)\
                        .join(Student, Feedback.student_id == Student.student_id)\
                        .all()
            return render_template('admin_login.html', feedbacks=feedbacks)
        else:
            flash("Invalid Admin Credentials!", "error")
    return render_template('admin_login.html', feedbacks=feedbacks)

# ---------------- STUDENT DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html', name=session['name'])

# ---------------- GIVE FEEDBACK ----------------
@app.route('/give_feedback', methods=['GET', 'POST'])
def give_feedback():
    if 'student_id' not in session:
        return redirect('/login')

    faculty = Faculty.query.all()
    student_id = session['student_id']

    if request.method == 'POST':
        faculty_id = int(request.form['faculty_id'])

        # ✅ Check if feedback already submitted
        existing_feedback = Feedback.query.filter_by(student_id=student_id, faculty_id=faculty_id).first()
        if existing_feedback:
            flash("You have already submitted feedback for this faculty!", "error")
            return redirect('/give_feedback')

        fb = Feedback(
            student_id=student_id,
            faculty_id=faculty_id,
            rating=request.form['rating'],
            comments=request.form['comments']
        )
        db.session.add(fb)
        db.session.commit()
        flash("Feedback submitted!", "success")
        return redirect('/give_feedback')

    return render_template('give_feedback.html', faculty=faculty)

# ---------------- VIEW OWN FEEDBACK ----------------
@app.route('/view_feedback')
def view_feedback():
    if 'student_id' not in session:
        return redirect('/login')

    feedbacks = db.session.query(Feedback, Faculty)\
        .join(Faculty, Feedback.faculty_id == Faculty.faculty_id)\
        .filter(Feedback.student_id == session['student_id'])\
        .all()

    return render_template('view_feedback.html', feedbacks=feedbacks)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)