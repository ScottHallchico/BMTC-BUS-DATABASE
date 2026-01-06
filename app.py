from flask import Flask, render_template, jsonify, request, redirect, url_for
import mysql.connector
import redis
import json

app = Flask(__name__)

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
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
    
    # 1. BUS Table
    cursor.execute("SELECT * FROM BUS")
    buses = cursor.fetchall()
    
    # 2. DRIVER Table
    cursor.execute("SELECT * FROM DRIVER")
    drivers = cursor.fetchall()

    # 3. STOP Table
    cursor.execute("SELECT * FROM STOP")
    stops = cursor.fetchall()

    # 4. ROUTE Table
    cursor.execute("SELECT * FROM ROUTE")
    routes = cursor.fetchall()

    # 5. ROUTE_STOP Table (Joined for readability)
    cursor.execute("""
        SELECT rs.route_stop_id, r.code as route_code, s.name as stop_name, rs.sequence_no
        FROM ROUTE_STOP rs
        JOIN ROUTE r ON rs.route_id = r.route_id
        JOIN STOP s ON rs.stop_id = s.stop_id
        ORDER BY r.code, rs.sequence_no
    """)
    route_stops = cursor.fetchall()

    # 6. TRIP Table (Joined with Route info)
    cursor.execute("""
        SELECT t.trip_id, r.code as route_code, t.scheduled_date, t.scheduled_start_time, t.status
        FROM TRIP t
        JOIN ROUTE r ON t.route_id = r.route_id
        ORDER BY t.scheduled_date DESC, t.scheduled_start_time ASC
    """)
    trips = cursor.fetchall()

    # 7. TRIP_ASSIGNMENT Table (Fully Joined)
    cursor.execute("""
        SELECT ta.assignment_id, t.trip_id, r.code as route_code, b.reg_no, d.name as driver_name, ta.assignment_time
        FROM TRIP_ASSIGNMENT ta
        JOIN TRIP t ON ta.trip_id = t.trip_id
        JOIN ROUTE r ON t.route_id = r.route_id
        LEFT JOIN BUS b ON ta.bus_id = b.bus_id
        LEFT JOIN DRIVER d ON ta.driver_id = d.driver_id
    """)
    assignments = cursor.fetchall()

    db.close()
    
    return render_template('dashboard.html', 
                           buses=buses, 
                           drivers=drivers,
                           stops=stops,
                           routes=routes,
                           route_stops=route_stops,
                           trips=trips,
                           assignments=assignments)

@app.route('/api/locations')
def get_locations():
    keys = r.keys("bus_location:*")
    buses = []
    for key in keys:
        try:
            data = json.loads(r.get(key))
            buses.append(data)
        except:
            pass
    return jsonify(buses)

if __name__ == '__main__':
    app.run(debug=True, port=5000)