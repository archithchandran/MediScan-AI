from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from model import predict_risk

app = Flask(__name__)
app.secret_key = "healthcare"

# Database Init
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  email TEXT,
                  password TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  bp REAL,
                  sugar REAL,
                  bmi REAL,
                  heart REAL,
                  risk TEXT,
                  reason TEXT,
                  doctor TEXT,
                  category TEXT,
                  date TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS appointments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  doctor TEXT,
                  date TEXT)''')

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                  (request.form['name'], request.form['email'], request.form['password']))
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?",
                  (request.form['email'], request.form['password']))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/analyze_page')
def analyze_page():
    return render_template('analyze.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    bp = float(request.form['bp'])
    sugar = float(request.form['sugar'])
    bmi = float(request.form['bmi'])
    heart = float(request.form['heart'])
    category = request.form['category']

    risk = predict_risk(bp, sugar, bmi, heart)

    reason = "Values are normal"
    if risk == "High":
        reason = "One or more parameters are very high"
    elif risk == "Medium":
        reason = "Some parameters are slightly high"

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
    c.execute("INSERT INTO records (user_id,bp,sugar,bmi,heart,risk,reason,doctor,category,date) VALUES (?,?,?,?,?,?,?,?,?,?)",
              (session['user_id'],bp,sugar,bmi,heart,risk,reason,doctor,category,date))
    conn.commit()
    conn.close()

    return render_template('result.html', risk=risk, reason=reason, doctor=doctor)

@app.route('/history')
def history():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT bp,sugar,bmi,heart,risk,reason,doctor,category,date FROM records WHERE user_id=?",(session['user_id'],))
    data = c.fetchall()
    conn.close()
    return render_template('history.html', data=data)

@app.route('/graph')
def graph():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT date, bmi FROM records WHERE user_id=?", (session['user_id'],))
    data = c.fetchall()
    conn.close()

    dates = [row[0] for row in data]
    bmi = [row[1] for row in data]

    plt.figure()
    plt.plot(dates, bmi)
    plt.xlabel("Date")
    plt.ylabel("BMI")
    plt.title("BMI History")
    plt.savefig("static/graph.png")

    return render_template('graph.html')

@app.route('/download_report')
def download_report():
    file_path = "static/report.pdf"
    c = canvas.Canvas(file_path)
    c.drawString(100, 750, "Smart Healthcare Report")
    c.drawString(100, 720, "AI Generated Health Report")
    c.save()
    return redirect("/static/report.pdf")

@app.route('/book', methods=['GET','POST'])
def book():
    if request.method == 'POST':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO appointments (user_id, doctor, date) VALUES (?,?,?)",
                  (session['user_id'], request.form['doctor'], request.form['date']))
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    return render_template('book.html')

@app.route('/admin')
def admin():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    msg = request.form['message'].lower()

    if "bp" in msg:
        return "Normal BP is 90-120. Exercise and reduce salt."
    elif "diabetes" in msg:
        return "Control sugar with diet and exercise."
    elif "heart" in msg:
        return "Maintain cholesterol and exercise regularly."
    else:
        return "Consult a doctor for proper medical advice."

app.run(debug=True)