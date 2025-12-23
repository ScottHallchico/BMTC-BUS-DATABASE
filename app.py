from flask import Flask, render_template, jsonify, request, redirect, url_for
import mysql.connector
import redis
import json

app = Flask(__name__)

# Connect to Redis (for live GPS)
r = redis.Redis(host='localhost', port=6379, db=0)

# 1. Home Page (Login)
@app.route('/')
def home():
    return render_template('index.html')

# 2. Login Logic
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    # Hardcoded for simplicity (In real life, check MySQL!)
    if username == "admin" and password == "admin123":
        return redirect(url_for('dashboard'))
    else:
        return "Invalid Credentials", 401

@app.route('/dashboard')
def dashboard():
    db = mysql.connector.connect(
        host="localhost", user="bmtc_admin", password="password123", database="bmtc_system"
    )
    cursor = db.cursor(dictionary=True)
    
    # 1. Fetch Fleet
    cursor.execute("SELECT * FROM Fleet")
    fleet_data = cursor.fetchall()
    
    # 2. Fetch Staff (Using your specific table name)
    cursor.execute("SELECT * FROM Staff")
    staff_data = cursor.fetchall()

    # 3. Fetch Schedule (Assuming you have this table, or creates an empty list if not)
    try:
        cursor.execute("SELECT * FROM Schedules")
        schedule_data = cursor.fetchall()
    except:
        schedule_data = [] # clear error if table doesn't exist yet

    db.close()
    
    # Send all three lists to the HTML
    return render_template('dashboard.html', 
                           fleet=fleet_data, 
                           staff=staff_data, 
                           schedules=schedule_data)

# 4. API for Live Map (The Frontend calls this every 1 second)
@app.route('/api/locations')
def get_locations():
    keys = r.keys("bus_location:*")
    buses = []
    for key in keys:
        data = json.loads(r.get(key))
        buses.append(data)
    return jsonify(buses)

if __name__ == '__main__':
    app.run(debug=True, port=5000)