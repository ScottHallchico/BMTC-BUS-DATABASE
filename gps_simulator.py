import redis
import time
import json
import mysql.connector
import random

# --- 1. Coordinate Dictionary ---
# These names must match the names in your 'STOP' table exactly.
LOCATIONS = {
    "Majestic": (12.9767, 77.5713),
    "Silk Board": (12.9172, 77.6227),
    "Hebbal": (13.0354, 77.5971),
    "Electronic City": (12.8452, 77.6602),
    "Airport": (13.1986, 77.7066),
    "ITPL": (12.9891, 77.7281),
    "Banashankari": (12.9255, 77.5468),
    "Attibele": (12.7783, 77.7715),
    "BTM Layout": (12.9166, 77.6101),
    "Pesit College": (12.9352, 77.5422),
    "Srinagar": (12.9427, 77.5529),
    "Domlur": (12.9600, 77.6412),
    "Bannerghatta NP": (12.8009, 77.5777),
    "Tindlu": (13.0617, 77.5636),
    "CV Raman Nagar": (12.9868, 77.6681),
    "HSR Layout": (12.9121, 77.6446),
    "Yelahanka": (13.1005, 77.5946),
    "Kengeri": (12.9177, 77.4833),
    "Shivajinagar": (12.9863, 77.6067)
}

def generate_path_from_names(start_name, end_name, steps=30):
    # If coordinates are missing, default to Majestic -> Silk Board
    if start_name not in LOCATIONS or end_name not in LOCATIONS:
        start_coord = LOCATIONS["Majestic"]
        end_coord = LOCATIONS["Silk Board"]
    else:
        start_coord = LOCATIONS[start_name]
        end_coord = LOCATIONS[end_name]

    path = []
    lat_step = (end_coord[0] - start_coord[0]) / steps
    lng_step = (end_coord[1] - start_coord[1]) / steps
    
    for i in range(steps):
        new_lat = start_coord[0] + (lat_step * i)
        new_lng = start_coord[1] + (lng_step * i)
        path.append((new_lat, new_lng))
        
    path.append(end_coord)
    return path

# --- 2. Database Connection & Setup ---
r = redis.Redis(host='localhost', port=6379, db=0)

try:
    db = mysql.connector.connect(
        host="localhost", user="bmtc_admin", password="password123", database="bmtc_system"
    )
    cursor = db.cursor(dictionary=True)

    # A. Fetch Active Assignments (Replaces the old 'Schedules' query)
    # We join TRIP_ASSIGNMENT -> TRIP -> ROUTE
    query = """
        SELECT ta.bus_id, t.route_id
        FROM TRIP_ASSIGNMENT ta
        JOIN TRIP t ON ta.trip_id = t.trip_id
        WHERE t.status != 'Completed'
    """
    cursor.execute(query)
    assignments = cursor.fetchall()
    
    # B. Fetch All Buses (to idle those not assigned)
    cursor.execute("SELECT bus_id FROM BUS")
    all_buses = [row['bus_id'] for row in cursor.fetchall()]

    scheduled_buses = []
    bus_states = {}

    print(f"✅ Found {len(assignments)} active assignments.")

    # C. Process Routes
    for item in assignments:
        bid = item['bus_id']
        rid = item['route_id']

        # Get Start Stop (Lowest sequence_no)
        cursor.execute("""
            SELECT s.name 
            FROM ROUTE_STOP rs 
            JOIN STOP s ON rs.stop_id = s.stop_id 
            WHERE rs.route_id = %s 
            ORDER BY rs.sequence_no ASC LIMIT 1
        """, (rid,))
        start_row = cursor.fetchone()

        # Get End Stop (Highest sequence_no)
        cursor.execute("""
            SELECT s.name 
            FROM ROUTE_STOP rs 
            JOIN STOP s ON rs.stop_id = s.stop_id 
            WHERE rs.route_id = %s 
            ORDER BY rs.sequence_no DESC LIMIT 1
        """, (rid,))
        end_row = cursor.fetchone()

        if start_row and end_row:
            start_name = start_row['name']
            end_name = end_row['name']
            
            path = generate_path_from_names(start_name, end_name)
            
            bus_states[bid] = {
                "route": path,
                "idx": random.randint(0, len(path) - 1),
                "dir": 1
            }
            scheduled_buses.append(bid)
            print(f"Bus {bid}: Route {rid} ({start_name} -> {end_name})")

    db.close()

except Exception as e:
    print(f"❌ Database Error: {e}")
    scheduled_buses = []
    all_buses = []

# D. Handle Idle Buses (Park at Majestic)
for bid in all_buses:
    if bid not in scheduled_buses:
        # Stationary bus at Majestic
        default_path = generate_path_from_names("Majestic", "Majestic", steps=1)
        bus_states[bid] = {
            "route": default_path,
            "idx": 0,
            "dir": 0 
        }

# --- 3. Simulation Loop ---
print("🚀 Simulation Running...")

while True:
    for bus_id, state in bus_states.items():
        route = state["route"]
        idx = state["idx"]
        
        curr_lat, curr_lng = route[idx]

        # Construct JSON data
        data = {
            "bus_id": bus_id,
            "lat": curr_lat,
            "lng": curr_lng,
            "speed": 40 if state["dir"] != 0 else 0,
            "timestamp": time.time()
        }
        
        # Save to Redis
        r.set(f"bus_location:{bus_id}", json.dumps(data))

        # Move logic
        if state["dir"] != 0:
            next_idx = idx + state["dir"]
            # Reverse direction if hitting the end
            if next_idx >= len(route) or next_idx < 0:
                state["dir"] *= -1
                next_idx = idx + state["dir"]
            state["idx"] = next_idx

    time.sleep(1)