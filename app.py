from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import func
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///enrollment.db'
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.secret_key = 'super-secret-key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'signin'

admin = Admin(app, name='ACME University', template_mode='bootstrap3')

# models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    role = db.Column(db.String)

    def check_password(self, password):
        return self.password == password

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    teacher = db.Column(db.String)
    time = db.Column(db.String)
    capacity = db.Column(db.Integer)
    enrollments = db.relationship('Enrollment', backref='course')

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    grade = db.Column(db.Integer)

class StudentGrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    grade = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {"name": self.name, "grade": self.grade}

with app.app_context():
    db.create_all()
    
    if not Course.query.first():
        course1 = Course(name="Math 141")
        db.session.add(course1)
        db.session.commit()

        enrollment1 = Enrollment(student_name="Bob Johnson", course_id=course1.id, grade=96)
        enrollment2 = Enrollment(student_name="Rachel Lovelace", course_id=course1.id, grade=82)
        db.session.add_all([enrollment1, enrollment2])
        db.session.commit()

    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', password='adminpass', role='admin')
        db.session.add(admin_user)
        db.session.commit()

    if not User.query.filter_by(username='teacher1').first():
        teacher_user = User(username='teacher1', password='teachpass', role='teacher')
        db.session.add(teacher_user)
        db.session.commit()

    if not Enrollment.query.first():
        cs_course = Course.query.filter_by(name="Math 141").first()
        if cs_course:
            enrollment1 = Enrollment(student_name="Alice Smith", course_id=cs_course.id, grade=90)
            enrollment2 = Enrollment(student_name="Bob Jones", course_id=cs_course.id, grade=85)
            db.session.add_all([enrollment1, enrollment2])
            db.session.commit()

    if not Course.query.filter_by(teacher='teacher1').first():
        sample_course = Course(
            name="Math 141",
            teacher="teacher1",  # This should match your teacher's username
            time="MWF 10:00-11:00",
            capacity=30
        )
        db.session.add(sample_course)
        db.session.commit()
    
    if not Course.query.filter_by(teacher='teacher1').first():
        sample_course = Course(
            name="CSE 108",
            teacher="teacher1",  # This should match your teacher's username
            time="TH 10:00-11:00",
            capacity=30
        )
        db.session.add(sample_course)
        db.session.commit()


#admin view
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('signin'))

admin.add_view(SecureModelView(User, db.session))
admin.add_view(SecureModelView(Course, db.session))
admin.add_view(SecureModelView(Enrollment, db.session))
admin.add_view(SecureModelView(StudentGrade, db.session))

# login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#routes
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        if user.role == 'admin':
            return redirect('/admin')
        elif user.role == 'teacher':
            return redirect('/teacher-home')
        elif user.role == 'student':
            return redirect('/my-classes')
    return redirect('/signin')

@app.route('/admin-login', methods=['POST'])
def admin_login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password) and user.role == 'admin':
        login_user(user)
        if user.role == 'admin':
            return redirect('/admin')
    # return redirect('/')
        else:
            return redirect('/courses')
    else:
        return redirect('/signin')


@app.route('/signin')
def signin():
    return render_template('mainhomepage.html')

@app.route('/enrollment/<int:enrollment_id>')
def show_enrollment(enrollment_id):
    with app.app_context():
        enrollment = db.session.query(Enrollment).filter_by(id=enrollment_id).first()
        if enrollment:
            return render_template('studentlogin.html', enrollment=enrollment)
        else:
            return "Enrollment is not in the system."

@app.route('/enrollments')
def list_enrollments():
    with app.app_context():
        enrollments = db.session.query(Enrollment).all()
        

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/signin')

@app.route('/')
def home():
    return redirect(url_for('signin'))
    

@app.cli.command("init-db")
def initialize_data():
    """Initialize the database with admin user"""
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', password='adminpass', role='admin')
        db.session.add(admin_user)
        db.session.commit()
    print("(username: 'admin', password: 'adminpass')")

#more.. 
@app.route('/my-classes')
@login_required
def my_classes():
    if current_user.role != 'student':
        return "Access denied. Students only."

    enrollments = Enrollment.query.filter_by(student_name=current_user.username).all()
    classes = [e.course for e in enrollments]
    return render_template('courses.html', classes=classes)

@app.route('/all-classes')
@login_required
def all_classes():
    if current_user.role != 'student':
        return "Access denied. Students only."

    classes = Course.query.all()
    return render_template('all_classes.html', classes=classes)

@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        return "Access denied. Students only."

    course = Course.query.get(course_id)

    if not course:
        return "Course not found."

    # Check capacity
    if len(course.enrollments) >= course.capacity:
        return "Class is full."

    # Prevent duplicate enrollment
    existing = Enrollment.query.filter_by(course_id=course.id, student_name=current_user.username).first()
    if existing:
        return "You are already enrolled."

    new_enrollment = Enrollment(student_name=current_user.username, course_id=course.id, grade=0)
    db.session.add(new_enrollment)
    db.session.commit()
    return redirect(url_for('my_classes'))

# ---------- TEACHER SECTION ----------

@app.route('/teacher-home')
@login_required
def teacher_home():
    if current_user.role != 'teacher':
        return "Access denied. Teachers only."

    courses = Course.query.filter_by(teacher=current_user.username).all()
    return render_template('teacher_home_tabs.html', courses=courses)
    
@app.route('/api/grades', methods=['GET'])
def get_all_grades():
    grades = StudentGrade.query.all()
    return jsonify([student.to_dict() for student in grades])

@app.route('/api/grades/<name>', methods=['GET'])
def get_student_grade(name):
    student = StudentGrade.query.filter_by(name=name).first()
    if student is None:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(student.to_dict())

@app.route('/api/grades', methods=['POST'])
def create_student():
    data = request.get_json()
    name = data.get("name")
    grade = data.get("grade")

    if StudentGrade.query.filter_by(name=name).first():
        return jsonify({"error": "Student already exists"}), 400

    max_id = db.session.query(func.max(StudentGrade.id)).scalar()
    new_id = (max_id or 0) + 1

    new_student = StudentGrade(id=new_id, name=name, grade=grade)
    db.session.add(new_student)
    db.session.commit()

    return jsonify(new_student.to_dict())

@app.route('/api/grades/<name>', methods=['PUT'])
def edit_student(name):
    data = request.get_json()
    grade = data.get("grade")
    student = StudentGrade.query.filter_by(name=name).first()

    if student is None:
        return jsonify({"error": "Student not found"}), 404

    student.grade = grade
    db.session.commit()
    return jsonify(student.to_dict())

@app.route('/api/grades/<name>', methods=['DELETE'])
def delete_student(name):
    student = StudentGrade.query.filter_by(name=name).first()
    if student is None:
        return jsonify({"error": "Student not found"}), 404

    db.session.delete(student)
    db.session.commit()
    return jsonify({"message": f"Student {name} deleted"})

@app.route('/teacher-classes')
@login_required
def teacher_classes():
    if current_user.role != 'teacher':
        return "Access denied. Teachers only."
    
    courses = Course.query.filter_by(teacher=current_user.username).all()
    return render_template('teacher_classes.html', courses=courses)

@app.route('/teacher-class/<int:course_id>')
@login_required
def class_roster(course_id):
    if current_user.role != 'teacher':
        return "Access denied. Teachers only."

    course = Course.query.get(course_id)
    if not course or course.teacher != current_user.username:
        return "Course not found or unauthorized."

    return render_template('class_roster.html', course=course, enrollments=course.enrollments)

@app.route('/edit-grade/<int:enrollment_id>', methods=['POST'])
@login_required
def edit_grade(enrollment_id):
    if current_user.role != 'teacher':
        return "Access denied. Teachers only."

    enrollment = Enrollment.query.get(enrollment_id)
    if not enrollment:
        return "Enrollment not found."

    course = Course.query.get(enrollment.course_id)
    if course.teacher != current_user.username:
        return "Unauthorized."

    new_grade = request.form.get("grade")
    enrollment.grade = int(new_grade)
    db.session.commit()
    return redirect(f"/teacher-class/{course.id}")


if __name__ == '__main__':
    app.run(debug=True)
