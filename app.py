import os
import sqlite3

from functools import wraps 
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g
)

# 1. python app.py --initdb # run once to create the database
# 2. python app.py
# 3. http://localhost:5000/login
# 4. username: admin, password: password

# 5. http://localhost:5000/dashboard
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key' 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'hw13.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'schema.sql')

USERNAME = 'admin'
PASSWORD = 'password'

# Connect to the database and set up a row factory for dict-like access
def get_db():
    if 'db_conn' not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  
        g.db_conn = conn
    return g.db_conn

# Teardown the database connection after each request
@app.teardown_appcontext
def close_db(exception=None):
    conn = g.pop('db_conn', None)
    if conn is not None:
        conn.close()


def init_db():
    # Create the database file if it doesn't exist
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError('schema.sql not found')

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    # Insert demo data if the tables are empty
    # If demo data already exists, this will not insert duplicates
    conn.execute("INSERT OR IGNORE INTO students (id, first_name, last_name) VALUES (1,'Franklyn','Collaguazo');")
    conn.execute("INSERT OR IGNORE INTO quizzes  (id, subject, num_questions, quiz_date) VALUES (1,'Software Eng Level 2',10,'2025-04-05');")
    conn.execute("INSERT OR IGNORE INTO results  (student_id, quiz_id, score) VALUES (1,1,71);")
    conn.commit()
    conn.close()

# Authentication 
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapper


#login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if username == USERNAME and password == PASSWORD:
            session.clear()
            session['logged_in'] = True
            flash('You have logged in', 'success')
            return redirect(url_for('dashboard'))
        flash('Wrong username or password', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    students = db.execute('SELECT * FROM students ORDER BY id').fetchall()
    quizzes  = db.execute('SELECT * FROM quizzes  ORDER BY id').fetchall()
    return render_template('dashboard.html', students=students, quizzes=quizzes)

# student page for adding new students
@app.route('/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        first = request.form.get('first_name', '').strip()
        last  = request.form.get('last_name', '').strip()
        if not first or not last:
            flash('First and last name required.', 'danger')
            return render_template('add_student.html')
        db = get_db()
        db.execute('INSERT INTO students (first_name, last_name) VALUES (?,?)', (first, last))
        db.commit()
        flash('Student has been added to the list', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_student.html')

# dynamic student id page 

@app.route('/student/<int:student_id>')
@login_required
def student_results(student_id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    if student is None:
        flash('Student does not exists in database.', 'warning')
        return redirect(url_for('dashboard'))

    results = db.execute(
        '''SELECT r.quiz_id, q.subject, q.quiz_date, r.score
             FROM results r
             JOIN quizzes q ON q.id = r.quiz_id
            WHERE r.student_id = ?
            ORDER BY q.quiz_date''',
        (student_id,)).fetchall()
    return render_template('student_results.html', student=student, results=results)

# Quiz Functionality Below

@app.route('/quiz/add', methods=['GET', 'POST'])
@login_required
def add_quiz():
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        num_questions = request.form.get('num_questions', type=int)
        quiz_date = request.form.get('quiz_date', '')  # yyyy-mm-dd
        if not subject or not num_questions or num_questions <= 0 or not quiz_date:
            flash('Complete all fields the number of questions must be > 0.', 'danger')
            return render_template('add_quiz.html')
        db = get_db()
        db.execute('INSERT INTO quizzes (subject, num_questions, quiz_date) VALUES (?,?,?)',
                   (subject, num_questions, quiz_date))
        db.commit()
        flash('Quiz added.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_quiz.html')

@app.route('/results/add', methods=['GET', 'POST'])
@login_required
def add_result():
    db = get_db()
    students = db.execute('SELECT id, first_name, last_name FROM students').fetchall()
    quizzes  = db.execute('SELECT id, subject FROM quizzes').fetchall()

    if request.method == 'POST':
        student_id = request.form.get('student_id', type=int)
        quiz_id = request.form.get('quiz_id', type=int)
        score = request.form.get('score', type=int)
        if (student_id is None or quiz_id is None or score is None
                or score < 0 or score > 100):
            flash('Select a student.', 'danger')
            return render_template('add_result.html', students=students, quizzes=quizzes)
        db.execute('INSERT INTO results (student_id, quiz_id, score) VALUES (?,?,?)',
                   (student_id, quiz_id, score))
        db.commit()
        flash('Result recorded.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_result.html', students=students, quizzes=quizzes)

# Run server and automatically create the database if it doesn't exist
if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        init_db()
        print('Database created and dummy demo data loaded.')
    app.run(debug=True)
