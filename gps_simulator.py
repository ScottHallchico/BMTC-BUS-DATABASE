import redis
import time
import random
import json
import mysql.connector

# 1. Connect to MySQL (To get the list of valid buses)
db = mysql.connector.connect(
    host="localhost",
    user="bmtc_admin",      # <--- New User
    password="password123", # <--- New Password
    database="bmtc_system"
)
cursor = db.cursor()

# Fetch all Bus IDs from the Fleet table
cursor.execute("SELECT bus_id FROM Fleet")
bus_ids = [row[0] for row in cursor.fetchall()] # Converts [(1,), (2,)...] to [1, 2...]
print(f"✅ Loaded {len(bus_ids)} buses from MySQL: {bus_ids}")
db.close() # We don't need MySQL anymore, we have the IDs.

# 2. Connect to Redis (To save live locations)
r = redis.Redis(host='localhost', port=6379, db=0)

# 3. Assign random starting positions around Bengaluru
# Bengaluru Center: 12.9716, 77.5946
bus_positions = {}
for bid in bus_ids:
    # Randomize start points slightly so they aren't all stacked on top of each other
    start_lat = 12.97 + random.uniform(-0.05, 0.05)
    start_lng = 77.59 + random.uniform(-0.05, 0.05)
    bus_positions[bid] = [start_lat, start_lng]

print("🚌 Smart GPS Simulator Started... (Press Ctrl+C to stop)")

# 4. The Simulation Loop
while True:
    for bus_id, coords in bus_positions.items():
        # Move the bus slightly (simulate driving)
        lat_change = random.uniform(-0.0005, 0.0005)
        lng_change = random.uniform(-0.0005, 0.0005)

        coords[0] += lat_change
        coords[1] += lng_change

        # Prepare data packet
        data = {
            "bus_id": bus_id,
            "lat": coords[0],
            "lng": coords[1],
            "speed": random.randint(20, 60),
            "timestamp": time.time()
        }

        # Save to Redis
        redis_key = f"bus_location:{bus_id}"
        r.set(redis_key, json.dumps(data))
        
        # Optional: Print only the first bus so terminal isn't too spammy
        if bus_id == 1:
            print(f"Updating 30 Buses... (Bus 1 is at {coords[0]:.4f}, {coords[1]:.4f})")

    # Wait 2 seconds (Real-time updates)
    time.sleep(2)