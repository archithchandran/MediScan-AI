from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from model import predict_risk
import hashlib

app = Flask(__name__)
app.secret_key = "mediscan"

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS doctors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT,
        specialization TEXT,
        license TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        bp REAL,
        sugar REAL,
        bmi REAL,
        heart REAL,
        risk TEXT,
        reason TEXT,
        doctor TEXT,
        category TEXT,
        date TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        doctor TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- PASSWORD HASH ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('index.html')

# ---------------- USER REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = hash_password(request.form['password'])

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                  (name,email,password))
        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template('register.html')

# ---------------- USER LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?",
                  (email,password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/dashboard')

    return render_template('login.html')

# ---------------- PROFILE ----------------
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name,email FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    conn.close()

    return render_template('profile.html', user=user)

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# ---------------- ANALYZE PAGE ----------------
@app.route('/analyze_page')
def analyze_page():
    return render_template('analyze.html')

# ---------------- ANALYZE HEALTH ----------------
@app.route('/analyze', methods=['POST'])
def analyze():
    bp = float(request.form['bp'])
    sugar = float(request.form['sugar'])
    bmi = float(request.form['bmi'])
    heart = float(request.form['heart'])
    category = request.form['category']

    risk = predict_risk(bp, sugar, bmi, heart)

    doctor = "General Physician"
    if category == "Heart":
        doctor = "Cardiologist"
    elif category == "Skin":
        doctor = "Dermatologist"
    elif category == "Diabetes":
        doctor = "Endocrinologist"

    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""INSERT INTO records 
              (user_id,bp,sugar,bmi,heart,risk,reason,doctor,category,date)
              VALUES (?,?,?,?,?,?,?,?,?,?)""",
              (session['user_id'],bp,sugar,bmi,heart,risk,"Health analyzed",doctor,category,date))
    conn.commit()
    conn.close()

    return render_template('result.html', risk=risk, doctor=doctor)

# ---------------- HISTORY ----------------
@app.route('/history')
def history():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM records WHERE user_id=?", (session['user_id'],))
    data = c.fetchall()
    conn.close()
    return render_template('history.html', data=data)

# ---------------- GRAPH ----------------
@app.route('/graph')
def graph():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT date, bmi FROM records WHERE user_id=?", (session['user_id'],))
    data = c.fetchall()
    conn.close()

    if len(data) == 0:
        return "No data available"

    dates = [row[0] for row in data]
    bmi = [row[1] for row in data]

    plt.figure()
    plt.plot(dates, bmi, marker='o')
    plt.xticks(rotation=45)
    plt.xlabel("Date")
    plt.ylabel("BMI")
    plt.title("Your BMI History")
    plt.tight_layout()
    plt.savefig("static/graph.png")
    plt.close()

    return render_template('graph.html')

# ---------------- PDF REPORT ----------------
@app.route('/download_report')
def download_report():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""SELECT bp,sugar,bmi,heart,risk,doctor,date 
                 FROM records WHERE user_id=? 
                 ORDER BY id DESC LIMIT 1""", (session['user_id'],))
    record = c.fetchone()
    conn.close()

    if not record:
        return "No records available"

    file_path = "static/report.pdf"
    pdf = canvas.Canvas(file_path)

    pdf.drawString(200, 800, "MediScan AI Health Report")
    pdf.drawString(50, 750, f"Blood Pressure: {record[0]}")
    pdf.drawString(50, 730, f"Sugar Level: {record[1]}")
    pdf.drawString(50, 710, f"BMI: {record[2]}")
    pdf.drawString(50, 690, f"Heart Rate: {record[3]}")
    pdf.drawString(50, 670, f"Risk Level: {record[4]}")
    pdf.drawString(50, 650, f"Doctor Suggestion: {record[5]}")
    pdf.drawString(50, 630, f"Date: {record[6]}")
    pdf.save()

    return redirect("/static/report.pdf")

# ---------------- BOOK APPOINTMENT ----------------
@app.route('/book', methods=['GET','POST'])
def book():
    if request.method == 'POST':
        doctor = request.form['doctor']
        date = request.form['date']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO appointments (user_id, doctor, date) VALUES (?,?,?)",
                  (session['user_id'], doctor, date))
        conn.commit()
        conn.close()
        return redirect('/dashboard')

    return render_template('book.html')

# ---------------- DOCTOR REGISTER ----------------
@app.route('/doctor_register', methods=['GET','POST'])
def doctor_register():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            specialization = request.form['specialization']
            license = request.form['license']

            conn = sqlite3.connect('database.db')
            c = conn.cursor()

            c.execute("""
            CREATE TABLE IF NOT EXISTS doctors(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                password TEXT,
                specialization TEXT,
                license TEXT
            )
            """)

            c.execute("INSERT INTO doctors (name,email,password,specialization,license) VALUES (?,?,?,?,?)",
                      (name,email,password,specialization,license))
            conn.commit()
            conn.close()

            return redirect('/doctor_login')

        except Exception as e:
            return str(e)

    return render_template('doctor_register.html')

# ---------------- DOCTOR LOGIN ----------------
@app.route('/doctor_login', methods=['GET','POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        license = request.form['license']

        valid_licenses = ["254678", "873452", "765289"]

        if license not in valid_licenses:
            return "Invalid License Number"

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM doctors WHERE email=? AND password=? AND license=?",
                  (email,password,license))
        doctor = c.fetchone()
        conn.close()

        if doctor:
            session['doctor_id'] = doctor[0]
            return redirect('/doctor_dashboard')

    return render_template('doctor_login.html')

# ---------------- DOCTOR DASHBOARD ----------------
@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'doctor_id' not in session:
        return redirect('/doctor_login')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM appointments")
    appointments = c.fetchall()

    c.execute("SELECT * FROM records")
    records = c.fetchall()

    conn.close()

    return render_template('doctor_dashboard.html', appointments=appointments, records=records)

# ---------------- ADMIN LOGIN ----------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == "archithc411@gmail.com" and password == "12345":
            session['admin'] = True
            return redirect('/admin_panel')
        else:
            return "Invalid Admin Credentials"

    return render_template('admin_login.html')

# ---------------- ADMIN PANEL ----------------
@app.route('/admin_panel')
def admin_panel():
    if 'admin' not in session:
        return redirect('/admin_login')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM users")
    users = c.fetchall()

    c.execute("SELECT * FROM doctors")
    doctors = c.fetchall()

    c.execute("SELECT * FROM records")
    records = c.fetchall()

    c.execute("SELECT * FROM appointments")
    appointments = c.fetchall()

    conn.close()

    return render_template('admin_panel.html',
                           users=users,
                           doctors=doctors,
                           records=records,
                           appointments=appointments)

# ---------------- AI CHAT ----------------
@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    msg = request.form['message'].lower()

    if "fever" in msg:
        return "Fever may be due to infection. Drink fluids and consult a doctor."
    elif "bp" in msg:
        return "Normal blood pressure is around 120/80."
    elif "diabetes" in msg:
        return "Control sugar with diet and exercise."
    else:
        return "Consult a doctor for accurate medical advice."

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)