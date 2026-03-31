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

# Password Hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Register
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = hash_password(request.form['password'])

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",(name,email,password))
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?",(email,password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/dashboard')

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Analyze Page
@app.route('/analyze_page')
def analyze_page():
    return render_template('analyze.html')

# Analyze Health
@app.route('/analyze', methods=['POST'])
def analyze():
    bp = float(request.form['bp'])
    sugar = float(request.form['sugar'])
    bmi = float(request.form['bmi'])
    heart = float(request.form['heart'])
    category = request.form['category']

    risk = predict_risk(bp, sugar, bmi, heart)

    reason = "Normal"
    if risk == "High":
        reason = "Health parameters are high"
    elif risk == "Medium":
        reason = "Parameters slightly high"

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

# History
@app.route('/history')
def history():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT bp,sugar,bmi,heart,risk,reason,doctor,category,date FROM records WHERE user_id=?",(session['user_id'],))
    data = c.fetchall()
    conn.close()
    return render_template('history.html', data=data)

# Graph
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

# PDF Report
@app.route('/download_report')
def download_report():
    file_path = "static/report.pdf"
    c = canvas.Canvas(file_path)
    c.drawString(100, 750, "MediScan AI Health Report")
    c.drawString(100, 720, "AI Generated Report")
    c.save()
    return redirect("/static/report.pdf")

# Appointment Booking
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

# Profile
@app.route('/profile')
def profile():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    conn.close()
    return render_template('profile.html', user=user)

# Admin Panel
@app.route('/admin')
def admin():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

# AI Chatbot
@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    msg = request.form['message'].lower()

    if "fever" in msg:
        return "You may have an infection. Stay hydrated and consult a doctor if fever persists."
    elif "bp" in msg:
        return "Normal blood pressure is 90-120. Reduce salt intake and exercise."
    elif "diabetes" in msg:
        return "Control sugar with diet, exercise and consult an endocrinologist."
    elif "medicine" in msg:
        return "Please consult a doctor before taking any medication."
    else:
        return "I recommend consulting a licensed medical professional for accurate diagnosis."

# Run App (Render Compatible)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)