import redis
import time
import json
import mysql.connector
import random

# --- 1. Coordinate Dictionary (The Translator) ---
# This maps your text names to real GPS points.
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
    "Pesit College": (12.9352, 77.5422), # PES University
    "Srinagar": (12.9427, 77.5529),
    "Domlur": (12.9600, 77.6412),
    "Bannerghatta NP": (12.8009, 77.5777),
    "Tindlu": (13.0617, 77.5636),
    "CV Raman Nagar": (12.9868, 77.6681),
    "HSR Layout": (12.9121, 77.6446),
    "Yelahanka": (13.1005, 77.5946),
    "Kengeri": (12.9177, 77.4833),
    "Yelahanka Satellite Town": (13.1095, 77.5843),
    "Vijayanagar": (12.9719, 77.5309),
    "Kadugodi": (12.9972, 77.7610),
    "Brigade Road": (12.9719, 77.6070),
    "E-City Phase 2": (12.8468, 77.6775),
    "Bannerghatta": (12.8633, 77.5936), # Bannerghatta Road area
    "Vidyaranyapura": (13.0766, 77.5577),
    "Shivajinagar": (12.9863, 77.6067)
}

# --- 2. Math Logic (Linear Interpolation) ---
def generate_path_from_names(start_name, end_name, steps=30):
    """
    Looks up coordinates for names and generates a straight line path.
    """
    if start_name not in LOCATIONS or end_name not in LOCATIONS:
        print(f"⚠️ Warning: Coordinates missing for {start_name} or {end_name}")
        # Default to Majestic -> Silk Board if unknown
        start_coord = LOCATIONS["Majestic"]
        end_coord = LOCATIONS["Silk Board"]
    else:
        start_coord = LOCATIONS[start_name]
        end_coord = LOCATIONS[end_name]

    # Generate points
    path = []
    lat_step = (end_coord[0] - start_coord[0]) / steps
    lng_step = (end_coord[1] - start_coord[1]) / steps
    
    for i in range(steps):
        new_lat = start_coord[0] + (lat_step * i)
        new_lng = start_coord[1] + (lng_step * i)
        path.append((new_lat, new_lng))
        
    path.append(end_coord)
    return path

# --- 3. Database Connection & Setup ---
r = redis.Redis(host='localhost', port=6379, db=0)

try:
    db = mysql.connector.connect(
        host="localhost", user="bmtc_admin", password="password123", database="bmtc_system"
    )
    cursor = db.cursor(dictionary=True)

    # Fetch Bus ID, Route ID, Start Point, End Point
    # JOIN Schedules and Routes tables
    query = """
    SELECT 
        s.bus_id, 
        s.route_id, 
        r.start_point, 
        r.end_point
    FROM Schedules s
    JOIN Routes r ON s.route_id = r.route_id
    """
    cursor.execute(query)
    scheduled_buses = cursor.fetchall()
    
    # Also get fleet just in case a bus is not scheduled
    cursor.execute("SELECT bus_id FROM Fleet")
    all_buses = [row['bus_id'] for row in cursor.fetchall()]
    
    db.close()
    print(f"✅ Loaded {len(scheduled_buses)} scheduled routes from Database.")

except Exception as e:
    print(f"❌ Database Error: {e}")
    scheduled_buses = []
    all_buses = []

# --- 4. Initialize Simulation State ---
bus_states = {}
scheduled_bus_ids = []

# A. Assign paths to Scheduled Buses
for item in scheduled_buses:
    bid = item['bus_id']
    start = item['start_point'].strip() # Remove spaces if any
    end = item['end_point'].strip()
    
    # Generate path dynamically!
    path = generate_path_from_names(start, end)
    
    bus_states[bid] = {
        "route": path,
        "idx": random.randint(0, len(path) - 1),
        "dir": 1
    }
    scheduled_bus_ids.append(bid)
    print(f"Bus {bid}: Route {item['route_id']} ({start} -> {end})")

# B. Handle Unscheduled Buses (Park them at Majestic)
for bid in all_buses:
    if bid not in scheduled_bus_ids:
        default_path = generate_path_from_names("Majestic", "Majestic", steps=1)
        bus_states[bid] = {
            "route": default_path,
            "idx": 0,
            "dir": 0 # Not moving
        }
        print(f"Bus {bid}: Idle (No Schedule)")

# --- 5. Run Loop ---
print("🚀 Simulation Running...")

while True:
    for bus_id, state in bus_states.items():
        route = state["route"]
        idx = state["idx"]
        
        curr_lat, curr_lng = route[idx]

        data = {
            "bus_id": bus_id,
            "lat": curr_lat,
            "lng": curr_lng,
            "speed": 40 if state["dir"] != 0 else 0,
            "timestamp": time.time()
        }
        
        r.set(f"bus_location:{bus_id}", json.dumps(data))

        # Move logic
        if state["dir"] != 0:
            next_idx = idx + state["dir"]
            if next_idx >= len(route) or next_idx < 0:
                state["dir"] *= -1
                next_idx = idx + state["dir"]
            state["idx"] = next_idx

    time.sleep(1)