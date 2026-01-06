from flask import Flask, render_template, jsonify, request, redirect, url_for
import mysql.connector
import redis
import json

app = Flask(__name__)

# -----------------------------
# Redis
# -----------------------------
r = redis.Redis(host='localhost', port=6379, db=0)

# -----------------------------
# DB helper
# -----------------------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="bmtc_admin",
        password="password123",
        database="bmtc_system"
    )

# -----------------------------
# Auth & Home
# -----------------------------
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    if request.form['username'] == "admin" and request.form['password'] == "admin123":
        return redirect(url_for('dashboard'))
    return "Invalid credentials", 401

# -----------------------------
# Dashboard
# -----------------------------
@app.route('/dashboard')
def dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM BUS")
    buses = cursor.fetchall()

    cursor.execute("SELECT * FROM DRIVER")
    drivers = cursor.fetchall()

    cursor.execute("SELECT * FROM STOP")
    stops = cursor.fetchall()

    cursor.execute("SELECT * FROM ROUTE")
    routes = cursor.fetchall()

    cursor.execute("""
        SELECT rs.route_stop_id, r.code AS route_code,
               s.name AS stop_name, rs.sequence_no
        FROM ROUTE_STOP rs
        JOIN ROUTE r ON rs.route_id = r.route_id
        JOIN STOP s ON rs.stop_id = s.stop_id
        ORDER BY r.code, rs.sequence_no
    """)
    route_stops = cursor.fetchall()

    cursor.execute("""
        SELECT t.trip_id, r.code AS route_code,
               t.scheduled_date, t.scheduled_start_time, t.status
        FROM TRIP t
        JOIN ROUTE r ON t.route_id = r.route_id
        ORDER BY t.scheduled_date DESC
    """)
    trips = cursor.fetchall()

    cursor.execute("""
        SELECT ta.assignment_id, t.trip_id, r.code AS route_code,
               b.reg_no, d.name AS driver_name, ta.assignment_time
        FROM TRIP_ASSIGNMENT ta
        JOIN TRIP t ON ta.trip_id = t.trip_id
        JOIN ROUTE r ON t.route_id = r.route_id
        LEFT JOIN BUS b ON ta.bus_id = b.bus_id
        LEFT JOIN DRIVER d ON ta.driver_id = d.driver_id
    """)
    assignments = cursor.fetchall()

    db.close()

    return render_template(
        "dashboard.html",
        buses=buses,
        drivers=drivers,
        stops=stops,
        routes=routes,
        route_stops=route_stops,
        trips=trips,
        assignments=assignments
    )

# -----------------------------
# BUS CRUD
# -----------------------------
@app.route('/bus/add', methods=['POST'])
def add_bus():
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO BUS (reg_no, capacity, status) VALUES (%s,%s,%s)",
        (
            request.form['reg_no'],
            request.form.get('capacity'),
            request.form.get('status', 'Active')
        )
    )
    db.commit()
    db.close()
    return redirect(url_for('dashboard'))


@app.route('/bus/delete/<int:bus_id>', methods=['POST'])
def delete_bus(bus_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM TRIP_ASSIGNMENT WHERE bus_id=%s", (bus_id,))
    if cursor.fetchone()[0] > 0:
        db.close()
        return "Bus is assigned to a trip", 400

    cursor.execute("DELETE FROM BUS WHERE bus_id=%s", (bus_id,))
    db.commit()
    db.close()
    return redirect(url_for('dashboard'))

# -----------------------------
# DRIVER CRUD
# -----------------------------
@app.route('/driver/add', methods=['POST'])
def add_driver():
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO DRIVER (name, phone) VALUES (%s,%s)",
        (request.form['name'], request.form.get('phone'))
    )
    db.commit()
    db.close()
    return redirect(url_for('dashboard'))


@app.route('/driver/delete/<int:driver_id>', methods=['POST'])
def delete_driver(driver_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM TRIP_ASSIGNMENT WHERE driver_id=%s", (driver_id,))
    if cursor.fetchone()[0] > 0:
        db.close()
        return "Driver is assigned to a trip", 400

    cursor.execute("DELETE FROM DRIVER WHERE driver_id=%s", (driver_id,))
    db.commit()
    db.close()
    return redirect(url_for('dashboard'))

# -----------------------------
# Live GPS API
# -----------------------------
@app.route('/api/locations')
def api_locations():
    data = []
    for key in r.keys("bus_location:*"):
        try:
            data.append(json.loads(r.get(key)))
        except:
            pass
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
