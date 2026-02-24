import base64, datetime, requests, os, re
from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from geopy.distance import geodesic

app = Flask(__name__)
CORS(app)

# --- 1. CONFIGURATION ---
CONSUMER_KEY = "Cg4GtJjtJDDvjsO6Fts4A1do7sx91rWMGyu5ktxl5YoxSWEx"
CONSUMER_SECRET = "T4PiebXPp8sRbsOumXR5PcPz4t6utH8kYXCUQcNOlWk7AOo7Xfyegb59WMGccdWf"
DARAJA_SHORTCODE = "174379"
DARAJA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

KUTUS_LOCATIONS = {
    "Spenza": (-0.5042, 37.2801), 
    "Diaspora": (-0.5080, 37.2850),
    "School": (-0.5015, 37.2805), 
    "Icon": (-0.5020, 37.2820),
    "Mjini": (-0.5150, 37.2950), 
    "Raha Premium": (-0.5065, 37.2835),
    "Ngomongo": (-0.5110, 37.2890)
}

# --- 2. STORAGE ---
students_db = {} # {name: password}
riders_db = []   # List of dicts: {name, plate, id, password, status}
pending_requests = [] 

def save_record(filename, entry):
    with open(filename, "a") as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | {entry}\n")

def reload_records():
    if os.path.exists("students_records.txt"):
        with open("students_records.txt", "r") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 2:
                    data = parts[1].split(":")
                    if len(data) == 2: students_db[data[0].strip()] = data[1].strip()
    
    if os.path.exists("riders_records.txt"):
        with open("riders_records.txt", "r") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 2:
                    r = parts[1].split(",") # name,plate,id,pass
                    if len(r) == 4:
                        riders_db.append({"name": r[0], "plate": r[1], "id": r[2], "password": r[3], "status": "unavailable"})

# --- 3. UPDATED AUTH LOGIC (UNIFIED) ---

@app.route('/auth/signup', methods=['POST'])
def signup():
    data = request.json
    role, name, password = data.get('role'), data.get('name'), data.get('password')
    
    if role == 'student':
        if name in students_db: return jsonify({"error": "Username taken"}), 400
        students_db[name] = password
        save_record("students_records.txt", f"{name}:{password}")
    else:
        plate, id_num = data.get('plate', '').upper(), str(data.get('id_number', ''))
        # Check for duplicates
        if any(r['plate'] == plate or r['id'] == id_num for r in riders_db):
            return jsonify({"error": "Plate or ID already registered"}), 400
        
        new_rider = {"name": name, "plate": plate, "id": id_num, "password": password, "status": "available"}
        riders_db.append(new_rider)
        save_record("riders_records.txt", f"{name},{plate},{id_num},{password}")
        
    return jsonify({"status": "success"}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    role, name, password = data.get('role'), data.get('name'), data.get('password')

    if role == 'student':
        if name in students_db and students_db[name] == password:
            return jsonify({"status": "success"}), 200
    else:
        rider = next((r for r in riders_db if r['name'] == name and r['password'] == password), None)
        if rider:
            rider['status'] = 'available'
            return jsonify({"status": "success", "plate": rider['plate']}), 200
            
    return jsonify({"error": "Invalid credentials"}), 401

# --- 4. UPDATED DISPATCH (DIRECT TARGETING) ---

@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json # Contains: student, to, fare, rider_plate
    data['time'] = datetime.datetime.now().strftime('%H:%M')
    # Use standard Google Maps URL format
    data['map_link'] = f"https://www.google.com/maps/dir/?api=1&destination=Kutus+{data['to']}"
    pending_requests.append(data)
    return jsonify({"status": "sent"}), 200

@app.route('/get_requests')
def get_requests():
    # DIRECT DISPATCH LOGIC: Filter by the rider's plate
    rider_plate = request.args.get('plate')
    if not rider_plate:
        return jsonify([])
    
    # Only return requests meant for THIS specific rider
    my_jobs = [r for r in pending_requests if r.get('rider_plate') == rider_plate]
    return jsonify(my_jobs)

# --- 5. RIDER STATUS & FARE ---

@app.route('/get_active_riders')
def get_active_riders():
    return jsonify([r for r in riders_db if r.get('status') == 'available'])

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    name, status = data.get('name'), data.get('status')
    for r in riders_db:
        if r['name'] == name:
            r['status'] = status
            return jsonify({"status": "success"}), 200
    return jsonify({"error": "Not found"}), 404

@app.route('/calculate_fare', methods=['POST'])
def calculate_fare():
    # Simple logic for Kutus boundaries
    return jsonify({"total_fare": 50})

if __name__ == '__main__':
    reload_records()
    app.run(host='0.0.0.0', port=10000)