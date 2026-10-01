# ============================================================
# UPDATED FINAL APP
# ML PREDICTION BUTTON + WORKING PREDICTION PAGE
# ============================================================


import sqlite3
import io
import os

from flask import (
    Flask, request, redirect, session,
    send_file
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


# ============================================================
# CONFIG
# ============================================================

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
DB_NAME = os.environ.get("DB_PATH", "student_performance_ml_final.db")


# ============================================================
# DATABASE
# ============================================================

def get_db():

    conn = sqlite3.connect(DB_NAME)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT UNIQUE,
        name TEXT,
        email TEXT,
        class_name TEXT,
        parent_id INTEGER,
        teacher_id INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS subjects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS marks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        subject_id INTEGER,
        marks REAL,
        max_marks REAL DEFAULT 100
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        total_classes INTEGER,
        attended_classes INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        message TEXT
    )
    """)

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    users = [
        ("admin", "admin123", "admin"),
        ("teacher1", "teacher123", "teacher"),
        ("student1", "student123", "student"),
        ("parent1", "parent123", "parent")
    ]

    for username, password, role in users:

        existing = conn.execute(
            "SELECT id FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if not existing:

            conn.execute("""
            INSERT INTO users(username,password,role)
            VALUES(?,?,?)
            """, (
                username,
                generate_password_hash(password),
                role
            ))

    # --------------------------------------------------------
    # SUBJECTS
    # --------------------------------------------------------

    subjects = [
        "Python",
        "DBMS",
        "Web Development",
        "Machine Learning",
        "Computer Networks"
    ]

    for subject in subjects:

        conn.execute(
            "INSERT OR IGNORE INTO subjects(name) VALUES(?)",
            (subject,)
        )

    # --------------------------------------------------------
    # USER IDS
    # --------------------------------------------------------

    teacher = conn.execute(
        "SELECT id FROM users WHERE username='teacher1'"
    ).fetchone()["id"]

    parent = conn.execute(
        "SELECT id FROM users WHERE username='parent1'"
    ).fetchone()["id"]

    # --------------------------------------------------------
    # STUDENTS
    # --------------------------------------------------------

    demo_students = [
        (
            "MCA001",
            "Demo Student",
            "student1@example.com",
            "MCA",
            parent,
            teacher
        ),
        (
            "MCA005",
            "Nitin Kumar",
            "nitin@example.com",
            "MCA",
            parent,
            teacher
        )
    ]

    for student in demo_students:

        conn.execute("""
        INSERT OR IGNORE INTO students
        (roll_no,name,email,class_name,parent_id,teacher_id)
        VALUES(?,?,?,?,?,?)
        """, student)

    # --------------------------------------------------------
    # DEMO MARKS
    # --------------------------------------------------------

    student = conn.execute("""
    SELECT id FROM students
    WHERE roll_no='MCA005'
    """).fetchone()

    if student:

        sid = student["id"]

        subject_rows = conn.execute("""
        SELECT id,name
        FROM subjects
        ORDER BY id
        """).fetchall()

        demo_marks = [78, 85, 72, 88, 80]

        for i, marks_value in enumerate(demo_marks):

            subject_id = subject_rows[i]["id"]

            exists = conn.execute("""
            SELECT id FROM marks
            WHERE student_id=? AND subject_id=?
            """, (
                sid,
                subject_id
            )).fetchone()

            if not exists:

                conn.execute("""
                INSERT INTO marks
                (student_id,subject_id,marks,max_marks)
                VALUES(?,?,?,100)
                """, (
                    sid,
                    subject_id,
                    marks_value
                ))

        # Attendance

        attendance = conn.execute("""
        SELECT id FROM attendance
        WHERE student_id=?
        """, (sid,)).fetchone()

        if not attendance:

            conn.execute("""
            INSERT INTO attendance
            (student_id,total_classes,attended_classes)
            VALUES(?,?,?)
            """, (
                sid,
                100,
                85
            ))

    conn.commit()

    conn.close()


init_db()


# ============================================================
# AUTH
# ============================================================

def get_current_user():

    if "user_id" not in session:
        return None

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return user


def logged_in():

    return "user_id" in session


# ============================================================
# STYLE
# ============================================================

STYLE = """

<style>

*{
    box-sizing:border-box;
}

body{
    margin:0;
    font-family:Arial,sans-serif;
    background:#f1f5f9;
    color:#1e293b;
}

.navbar{
    background:#172554;
    color:white;
    padding:18px 30px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.navbar a{
    color:white;
    text-decoration:none;
    margin-left:15px;
}

.container{
    max-width:1200px;
    margin:30px auto;
    padding:0 20px;
}

.card{
    background:white;
    padding:25px;
    border-radius:15px;
    margin-bottom:20px;
    box-shadow:0 5px 18px rgba(0,0,0,.08);
}

.grid{
    display:grid;
    grid-template-columns:
    repeat(auto-fit,minmax(220px,1fr));
    gap:20px;
}

.stat{
    background:white;
    padding:25px;
    border-radius:15px;
    box-shadow:0 5px 18px rgba(0,0,0,.08);
}

.stat h2{
    font-size:30px;
}

.menu{
    display:flex;
    flex-wrap:wrap;
    gap:12px;
    margin:20px 0;
}

.btn{
    display:inline-block;
    background:#2563eb;
    color:white;
    text-decoration:none;
    padding:11px 17px;
    border-radius:9px;
    border:none;
    cursor:pointer;
}

.btn-ml{
    background:#7c3aed;
}

.btn-success{
    background:#16a34a;
}

input,select{
    width:100%;
    padding:12px;
    margin:7px 0 15px;
    border:1px solid #cbd5e1;
    border-radius:8px;
}

table{
    width:100%;
    border-collapse:collapse;
}

th,td{
    padding:12px;
    border-bottom:1px solid #e2e8f0;
}

th{
    background:#eff6ff;
}

.prediction{
    text-align:center;
    padding:40px;
}

.prediction-number{
    font-size:55px;
    font-weight:bold;
    color:#7c3aed;
}

.badge{
    padding:6px 12px;
    border-radius:20px;
}

.safe{
    background:#dcfce7;
    color:#166534;
}

.risk{
    background:#fee2e2;
    color:#991b1b;
}

.login{
    max-width:430px;
    margin:80px auto;
}

.error{
    background:#fee2e2;
    color:#991b1b;
    padding:12px;
    border-radius:8px;
}

</style>
"""


def html_page(title, body):

    user = get_current_user()

    navbar = ""

    if user:

        navbar = f"""
        <div class="navbar">

            <b>🎓 Student Performance System</b>

            <div>
                {user['username']} ({user['role']})
                <a href="/dashboard">Dashboard</a>
                <a href="/logout">Logout</a>
            </div>

        </div>
        """

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>{title}</title>

        {STYLE}

    </head>

    <body>

        {navbar}

        <div class="container">

            {body}

        </div>

    </body>

    </html>
    """


# ============================================================
# LOGIN
# ============================================================

@app.route("/", methods=["GET","POST"])
def login():

    error = ""

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute("""
        SELECT *
        FROM users
        WHERE username=?
        """, (username,)).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["role"] = user["role"]

            return redirect("/dashboard")

        error = "Invalid username or password"

    return html_page(
        "Login",
        f"""

        <div class="login card">

            <h1>🎓 Login</h1>

            <p>
            Student Performance Analysis System
            </p>

            {
                f'<div class="error">{error}</div>'
                if error else ''
            }

            <form method="POST">

                <label>Username</label>

                <input
                    name="username"
                    required
                >

                <label>Password</label>

                <input
                    type="password"
                    name="password"
                    required
                >

                <button class="btn">
                    Login
                </button>

            </form>

            <hr>

            <b>Demo Login</b>

            <p>Admin: admin / admin123</p>

            <p>Teacher: teacher1 / teacher123</p>

            <p>Student: student1 / student123</p>

            <p>Parent: parent1 / parent123</p>

        </div>

        """
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():
        return redirect("/")

    user = get_current_user()

    conn = get_db()

    students = conn.execute(
        "SELECT COUNT(*) c FROM students"
    ).fetchone()["c"]

    subjects = conn.execute(
        "SELECT COUNT(*) c FROM subjects"
    ).fetchone()["c"]

    marks = conn.execute(
        "SELECT COUNT(*) c FROM marks"
    ).fetchone()["c"]

    conn.close()

    return html_page(
        "Dashboard",
        f"""

        <h1>
            Welcome {user['username']} 👋
        </h1>

        <div class="menu">

            <a class="btn"
               href="/students">
               👨‍🎓 Students
            </a>

            <a class="btn"
               href="/subjects">
               📚 Subjects
            </a>

            <a class="btn"
               href="/marks">
               📝 Marks
            </a>

            <a class="btn"
               href="/attendance">
               📅 Attendance
            </a>

            <a class="btn"
               href="/performance">
               📊 Performance
            </a>

            <!-- ML BUTTON -->
            <a class="btn btn-ml"
               href="/ml-prediction">
               🤖 ML Prediction
            </a>

            <a class="btn"
               href="/at-risk">
               ⚠️ At-Risk Students
            </a>

            <a class="btn btn-success"
               href="/excel">
               📥 Excel
            </a>

            <a class="btn"
               href="/pdf">
               📄 PDF Report
            </a>

        </div>


        <div class="grid">

            <div class="stat">

                <small>Total Students</small>

                <h2>{students}</h2>

            </div>

            <div class="stat">

                <small>Total Subjects</small>

                <h2>{subjects}</h2>

            </div>

            <div class="stat">

                <small>Marks Records</small>

                <h2>{marks}</h2>

            </div>

            <div class="stat">

                <small>ML Prediction</small>

                <h2>🤖</h2>

                <a class="btn btn-ml"
                   href="/ml-prediction">

                   Predict Next Score

                </a>

            </div>

        </div>


        <div class="card">

            <h2>🤖 Machine Learning</h2>

            <p>
            Use previous subject marks to estimate
            the student's next score using
            Linear Regression.
            </p>

            <a class="btn btn-ml"
               href="/ml-prediction">

               Open ML Prediction

            </a>

        </div>

        """
    )


# ============================================================
# STUDENTS
# ============================================================

@app.route("/students", methods=["GET","POST"])
def students_page():

    if not logged_in():
        return redirect("/")

    conn = get_db()

    if request.method == "POST":

        roll = request.form["roll"]
        name = request.form["name"]
        email = request.form["email"]
        class_name = request.form["class_name"]

        try:

            conn.execute("""
            INSERT INTO students
            (roll_no,name,email,class_name)
            VALUES(?,?,?,?)
            """, (
                roll,
                name,
                email,
                class_name
            ))

            conn.commit()

        except:
            pass

    rows = conn.execute("""
    SELECT *
    FROM students
    ORDER BY id DESC
    """).fetchall()

    conn.close()

    table = ""

    for s in rows:

        table += f"""
        <tr>

            <td>{s['roll_no']}</td>

            <td>{s['name']}</td>

            <td>{s['email']}</td>

            <td>{s['class_name']}</td>

        </tr>
        """

    return html_page(
        "Students",
        f"""

        <h1>👨‍🎓 Students</h1>

        <div class="card">

        <form method="POST">

            <input
                name="roll"
                placeholder="Roll Number"
                required
            >

            <input
                name="name"
                placeholder="Student Name"
                required
            >

            <input
                name="email"
                placeholder="Email"
            >

            <input
                name="class_name"
                placeholder="Class"
                value="MCA"
            >

            <button class="btn">
                Add Student
            </button>

        </form>

        </div>

        <div class="card">

        <table>

        <tr>
            <th>Roll</th>
            <th>Name</th>
            <th>Email</th>
            <th>Class</th>
        </tr>

        {table}

        </table>

        </div>

        """
    )


# ============================================================
# SUBJECTS
# ============================================================

@app.route("/subjects", methods=["GET","POST"])
def subjects_page():

    if not logged_in():
        return redirect("/")

    conn = get_db()

    if request.method == "POST":

        name = request.form["name"]

        conn.execute(
            "INSERT OR IGNORE INTO subjects(name) VALUES(?)",
            (name,)
        )

        conn.commit()

    rows = conn.execute(
        "SELECT * FROM subjects ORDER BY id"
    ).fetchall()

    conn.close()

    table = ""

    for s in rows:

        table += f"""
        <tr>
            <td>{s['id']}</td>
            <td>{s['name']}</td>
        </tr>
        """

    return html_page(
        "Subjects",
        f"""

        <h1>📚 Subjects</h1>

        <div class="card">

        <form method="POST">

            <input
                name="name"
                placeholder="Subject Name"
                required
            >

            <button class="btn">
                Add Subject
            </button>

        </form>

        </div>

        <div class="card">

        <table>

        <tr>
            <th>ID</th>
            <th>Subject</th>
        </tr>

        {table}

        </table>

        </div>

        """
    )


# ============================================================
# MARKS
# ============================================================

@app.route("/marks", methods=["GET","POST"])
def marks_page():

    if not logged_in():
        return redirect("/")

    conn = get_db()

    if request.method == "POST":

        student_id = request.form["student_id"]
        subject_id = request.form["subject_id"]
        marks_value = float(request.form["marks"])

        conn.execute("""
        INSERT INTO marks
        (student_id,subject_id,marks,max_marks)
        VALUES(?,?,?,100)
        """, (
            student_id,
            subject_id,
            marks_value
        ))

        conn.commit()

    students = conn.execute(
        "SELECT * FROM students ORDER BY name"
    ).fetchall()

    subjects = conn.execute(
        "SELECT * FROM subjects ORDER BY name"
    ).fetchall()

    rows = conn.execute("""
    SELECT
        s.roll_no,
        s.name student,
        sub.name subject,
        m.marks
    FROM marks m
    JOIN students s
    ON s.id=m.student_id
    JOIN subjects sub
    ON sub.id=m.subject_id
    ORDER BY m.id DESC
    """).fetchall()

    conn.close()

    student_options = ""

    for s in students:

        student_options += f"""
        <option value="{s['id']}">
            {s['roll_no']} - {s['name']}
        </option>
        """

    subject_options = ""

    for s in subjects:

        subject_options += f"""
        <option value="{s['id']}">
            {s['name']}
        </option>
        """

    table = ""

    for r in rows:

        table += f"""
        <tr>
            <td>{r['roll_no']}</td>
            <td>{r['student']}</td>
            <td>{r['subject']}</td>
            <td>{r['marks']}</td>
        </tr>
        """

    return html_page(
        "Marks",
        f"""

        <h1>📝 Marks</h1>

        <div class="card">

        <form method="POST">

            <label>Student</label>

            <select name="student_id">

                {student_options}

            </select>

            <label>Subject</label>

            <select name="subject_id">

                {subject_options}

            </select>

            <label>Marks</label>

            <input
                type="number"
                name="marks"
                min="0"
                max="100"
                required
            >

            <button class="btn">
                Save Marks
            </button>

        </form>

        </div>

        <div class="card">

        <table>

        <tr>
            <th>Roll</th>
            <th>Student</th>
            <th>Subject</th>
            <th>Marks</th>
        </tr>

        {table}

        </table>

        </div>

        """
    )


# ============================================================
# ATTENDANCE
# ============================================================

@app.route("/attendance", methods=["GET","POST"])
def attendance_page():

    if not logged_in():
        return redirect("/")

    conn = get_db()

    if request.method == "POST":

        student_id = request.form["student_id"]

        total = int(
            request.form["total"]
        )

        attended = int(
            request.form["attended"]
        )

        existing = conn.execute("""
        SELECT id
        FROM attendance
        WHERE student_id=?
        """, (student_id,)).fetchone()

        if existing:

            conn.execute("""
            UPDATE attendance
            SET total_classes=?,
                attended_classes=?
            WHERE student_id=?
            """, (
                total,
                attended,
                student_id
            ))

        else:

            conn.execute("""
            INSERT INTO attendance
            (student_id,total_classes,attended_classes)
            VALUES(?,?,?)
            """, (
                student_id,
                total,
                attended
            ))

        conn.commit()

    students = conn.execute(
        "SELECT * FROM students ORDER BY name"
    ).fetchall()

    rows = conn.execute("""
    SELECT
        s.roll_no,
        s.name,
        a.total_classes,
        a.attended_classes,
        ROUND(
            a.attended_classes*100.0/
            NULLIF(a.total_classes,0),2
        ) percentage
    FROM attendance a
    JOIN students s
    ON s.id=a.student_id
    ORDER BY s.name
    """).fetchall()

    conn.close()

    options = ""

    for s in students:

        options += f"""
        <option value="{s['id']}">
            {s['roll_no']} - {s['name']}
        </option>
        """

    table = ""

    for r in rows:

        table += f"""
        <tr>

            <td>{r['roll_no']}</td>

            <td>{r['name']}</td>

            <td>{r['total_classes']}</td>

            <td>{r['attended_classes']}</td>

            <td>{r['percentage']}%</td>

        </tr>
        """

    return html_page(
        "Attendance",
        f"""

        <h1>📅 Attendance</h1>

        <div class="card">

        <form method="POST">

            <label>Student</label>

            <select name="student_id">

                {options}

            </select>

            <input
                name="total"
                type="number"
                placeholder="Total Classes"
                required
            >

            <input
                name="attended"
                type="number"
                placeholder="Attended Classes"
                required
            >

            <button class="btn">
                Save Attendance
            </button>

        </form>

        </div>

        <div class="card">

        <table>

        <tr>
            <th>Roll</th>
            <th>Name</th>
            <th>Total</th>
            <th>Attended</th>
            <th>Attendance</th>
        </tr>

        {table}

        </table>

        </div>

        """
    )


# ============================================================
# PERFORMANCE
# ============================================================

@app.route("/performance")
def performance_page():

    if not logged_in():
        return redirect("/")

    conn = get_db()

    students = conn.execute(
        "SELECT * FROM students"
    ).fetchall()

    rows = ""

    for s in students:

        avg_row = conn.execute("""
        SELECT AVG(marks) avg
        FROM marks
        WHERE student_id=?
        """, (s["id"],)).fetchone()

        avg = avg_row["avg"] or 0

        attendance = conn.execute("""
        SELECT *
        FROM attendance
        WHERE student_id=?
        """, (s["id"],)).fetchone()

        attendance_pct = 0

        if attendance and attendance["total_classes"]:

            attendance_pct = (
                attendance["attended_classes"] /
                attendance["total_classes"]
            ) * 100

        if avg >= 90:
            grade = "A+"
        elif avg >= 80:
            grade = "A"
        elif avg >= 70:
            grade = "B"
        elif avg >= 60:
            grade = "C"
        elif avg >= 50:
            grade = "D"
        else:
            grade = "F"

        risk = (
            avg < 50 or
            attendance_pct < 75
        )

        status = (
            '<span class="badge risk">⚠️ At Risk</span>'
            if risk
            else
            '<span class="badge safe">✓ Safe</span>'
        )

        rows += f"""
        <tr>

            <td>{s['roll_no']}</td>

            <td>{s['name']}</td>

            <td>{avg:.2f}%</td>

            <td>{attendance_pct:.2f}%</td>

            <td>{grade}</td>

            <td>{status}</td>

        </tr>
        """

    conn.close()

    return html_page(
        "Performance",
        f"""

        <h1>📊 Performance Analysis</h1>

        <div class="card">

        <table>

        <tr>
            <th>Roll</th>
            <th>Student</th>
            <th>Average</th>
            <th>Attendance</th>
            <th>Grade</th>
            <th>Status</th>
        </tr>

        {rows}

        </table>

        </div>

        """
    )


# ============================================================
# ML PREDICTION
# ============================================================

@app.route("/ml-prediction")
def ml_prediction():

    if not logged_in():
        return redirect("/")

    user = get_current_user()

    conn = get_db()

    # --------------------------------------------------------
    # Student selection
    # --------------------------------------------------------

    if user["role"] == "student":

        student = conn.execute("""
        SELECT *
        FROM students
        WHERE roll_no='MCA001'
        OR email='student1@example.com'
        LIMIT 1
        """).fetchone()

    elif user["role"] == "parent":

        student = conn.execute("""
        SELECT *
        FROM students
        WHERE parent_id=?
        ORDER BY id
        LIMIT 1
        """, (user["id"],)).fetchone()

    else:

        # Admin / Teacher
        # Demo ML student = MCA005
        student = conn.execute("""
        SELECT *
        FROM students
        WHERE roll_no='MCA005'
        LIMIT 1
        """).fetchone()

    if not student:

        conn.close()

        return html_page(
            "ML Prediction",
            """
            <div class="card">

                <h2>⚠️ Student not found</h2>

                <p>
                Please add a student and marks first.
                </p>

            </div>
            """
        )

    # --------------------------------------------------------
    # Get marks
    # --------------------------------------------------------

    marks = conn.execute("""
    SELECT
        sub.name,
        m.marks
    FROM marks m
    JOIN subjects sub
    ON sub.id=m.subject_id
    WHERE m.student_id=?
    ORDER BY m.id
    """, (student["id"],)).fetchall()

    conn.close()

    values = [
        float(m["marks"])
        for m in marks
    ]

    prediction = None

    if len(values) >= 2:

        X = np.arange(
            1,
            len(values)+1
        ).reshape(-1,1)

        y = np.array(values)

        model = LinearRegression()

        model.fit(X,y)

        prediction = float(
            model.predict(
                [[len(values)+1]]
            )[0]
        )

        prediction = max(
            0,
            min(100,prediction)
        )

    # --------------------------------------------------------
    # Marks table
    # --------------------------------------------------------

    mark_rows = ""

    for i,m in enumerate(marks,1):

        mark_rows += f"""
        <tr>

            <td>{i}</td>

            <td>{m['name']}</td>

            <td>{m['marks']}%</td>

        </tr>
        """

    prediction_text = (
        f"{prediction:.2f}%"
        if prediction is not None
        else "Not enough data"
    )

    return html_page(
        "ML Prediction",
        f"""

        <h1>🤖 ML Prediction</h1>

        <div class="card">

            <h2>
                Student: {student['name']}
            </h2>

            <p>
                Roll Number:
                <b>{student['roll_no']}</b>
            </p>

        </div>


        <div class="card prediction">

            <h2>
                Predicted Next Score
            </h2>

            <div class="prediction-number">

                {prediction_text}

            </div>

            <p>
                Prediction is generated using
                Linear Regression based on
                previous marks.
            </p>

        </div>


        <div class="card">

            <h2>📚 Previous Marks</h2>

            <table>

                <tr>
                    <th>#</th>
                    <th>Subject</th>
                    <th>Marks</th>
                </tr>

                {mark_rows}

            </table>

        </div>


        <div class="card">

            <a class="btn"
               href="/dashboard">

               ← Back to Dashboard

            </a>

        </div>

        """
    )


# ============================================================
# AT-RISK
# ============================================================

@app.route("/at-risk")
def at_risk():

    if not logged_in():
        return redirect("/")

    conn = get_db()

    students = conn.execute(
        "SELECT * FROM students"
    ).fetchall()

    rows = ""

    for s in students:

        avg = conn.execute("""
        SELECT AVG(marks) avg
        FROM marks
        WHERE student_id=?
        """, (s["id"],)).fetchone()["avg"] or 0

        attendance = conn.execute("""
        SELECT *
        FROM attendance
        WHERE student_id=?
        """, (s["id"],)).fetchone()

        attendance_pct = 0

        if attendance and attendance["total_classes"]:

            attendance_pct = (
                attendance["attended_classes"] /
                attendance["total_classes"]
            ) * 100

        if avg < 50 or attendance_pct < 75:

            rows += f"""
            <tr>

                <td>{s['roll_no']}</td>

                <td>{s['name']}</td>

                <td>{avg:.2f}%</td>

                <td>{attendance_pct:.2f}%</td>

            </tr>
            """

    conn.close()

    return html_page(
        "At Risk",
        f"""

        <h1>⚠️ At-Risk Students</h1>

        <div class="card">

        <table>

        <tr>
            <th>Roll</th>
            <th>Name</th>
            <th>Average</th>
            <th>Attendance</th>
        </tr>

        {rows}

        </table>

        </div>

        """
    )


# ============================================================
# PDF
# ============================================================

@app.route("/pdf")
def pdf_report():

    if not logged_in():
        return redirect("/")

    conn = get_db()

    student = conn.execute("""
    SELECT *
    FROM students
    WHERE roll_no='MCA005'
    LIMIT 1
    """).fetchone()

    marks = conn.execute("""
    SELECT
        sub.name,
        m.marks
    FROM marks m
    JOIN subjects sub
    ON sub.id=m.subject_id
    WHERE m.student_id=?
    """, (student["id"],)).fetchall()

    attendance = conn.execute("""
    SELECT *
    FROM attendance
    WHERE student_id=?
    """, (student["id"],)).fetchone()

    conn.close()

    avg = np.mean([
        m["marks"] for m in marks
    ]) if marks else 0

    attendance_pct = 0

    if attendance:

        attendance_pct = (
            attendance["attended_classes"] /
            attendance["total_classes"]
        ) * 100

    buffer = io.BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4
    )

    width,height = A4

    pdf.setFont(
        "Helvetica-Bold",
        20
    )

    pdf.drawString(
        140,
        height-60,
        "STUDENT PERFORMANCE REPORT"
    )

    pdf.setFont(
        "Helvetica",
        12
    )

    pdf.drawString(
        60,
        height-110,
        f"Student: {student['name']}"
    )

    pdf.drawString(
        60,
        height-135,
        f"Roll No: {student['roll_no']}"
    )

    pdf.drawString(
        60,
        height-160,
        f"Average Marks: {avg:.2f}%"
    )

    pdf.drawString(
        60,
        height-185,
        f"Attendance: {attendance_pct:.2f}%"
    )

    y = height-230

    for m in marks:

        pdf.drawString(
            60,
            y,
            f"{m['name']}: {m['marks']}"
        )

        y -= 25

    pdf.drawString(
        60,
        y-20,
        "Generated by Student Performance Analysis System"
    )

    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="student_performance_report.pdf",
        mimetype="application/pdf"
    )


# ============================================================
# EXCEL
# ============================================================

@app.route("/excel")
def excel():

    if not logged_in():
        return redirect("/")

    conn = get_db()

    rows = conn.execute("""
    SELECT
        s.roll_no AS Roll_No,
        s.name AS Student_Name,
        s.class_name AS Class,
        ROUND(AVG(m.marks),2) AS Average_Marks
    FROM students s
    LEFT JOIN marks m
    ON s.id=m.student_id
    GROUP BY s.id
    """).fetchall()

    data = []

    for r in rows:

        data.append({
            "Roll No": r["Roll_No"],
            "Student Name": r["Student_Name"],
            "Class": r["Class"],
            "Average Marks": r["Average_Marks"] or 0
        })

    conn.close()

    df = pd.DataFrame(data)

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Performance"
        )

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="student_performance.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
