const express = require('express');
const mysql = require('mysql2');
const redis = require('redis');
const cors = require('cors');

const app = express();
app.use(cors()); // Allow frontend to connect
app.use(express.json());

// 1. MySQL Connection (Static Data)
const db = mysql.createConnection({
    host: 'localhost',
    user: 'bmtc_admin',      // Use the user we created
    password: 'password123', // <--- PUT YOUR PASSWORD HERE
    database: 'bmtc_system'
});

db.connect(err => {
    if (err) console.error('❌ MySQL Connection Failed:', err);
    else console.log('✅ Connected to MySQL');
});

// 2. Redis Connection (Live Data)
const redisClient = redis.createClient();
redisClient.connect()
    .then(() => console.log('✅ Connected to Redis'))
    .catch(err => console.error('❌ Redis Connection Failed:', err));

// ---------------------------------------------------------
// API ENDPOINT 1: Get All Routes (For the Dropdown)
// ---------------------------------------------------------
app.get('/api/routes', (req, res) => {
    const sql = "SELECT route_id, route_number, start_point, end_point FROM Routes";
    db.query(sql, (err, results) => {
        if (err) return res.status(500).json(err);
        res.json(results);
    });
});

// ---------------------------------------------------------
// API ENDPOINT 2: The "Hybrid" Query (Static + Live Data)
// ---------------------------------------------------------
app.get('/api/live-buses/:routeId', async (req, res) => {
    const routeId = req.params.routeId;

    // A. Query MySQL: "Which buses are scheduled on this route?"
    const sql = `
        SELECT s.bus_id, f.registration_number, f.bus_type, st.full_name as driver_name
        FROM Schedules s
        JOIN Fleet f ON s.bus_id = f.bus_id
        JOIN Staff st ON s.driver_id = st.staff_id
        WHERE s.route_id = ?
    `;

    db.query(sql, [routeId], async (err, buses) => {
        if (err) return res.status(500).json(err);

        // If no buses are found on this route
        if (buses.length === 0) return res.json([]);

        // B. Query Redis: "Where are these specific buses right now?"
        const busDataWithLocation = [];

        for (const bus of buses) {
            // Fetch live location from Redis Key "bus_location:{id}"
            const rawLocation = await redisClient.get(`bus_location:${bus.bus_id}`);
            
            let location = null;
            if (rawLocation) {
                location = JSON.parse(rawLocation);
            }

            // C. Merge Data: Combine SQL Info + Redis Location
            busDataWithLocation.push({
                ...bus, // Includes bus_id, reg_number, driver_name
                live_data: location // Includes lat, lng, speed
            });
        }

        // Send the combined list to the frontend
        res.json(busDataWithLocation);
    });
});

// Start the Server
app.listen(3000, () => {
    console.log('🚀 Server running on http://localhost:3000');
});