import base64, datetime, requests, os, re
from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from geopy.distance import geodesic 

app = Flask(__name__)
CORS(app)

# --- 1. CONFIGURATION ---
KUTUS_LOCATIONS = {
    "Spenza": (-0.5042, 37.2801), 
    "Diaspora": (-0.5080, 37.2850),
    "School": (-0.5015, 37.2805), 
    "Icon": (-0.5020, 37.2820),
    "Mjini": (-0.5150, 37.2950), 
    "Raha Premium": (-0.5065, 37.2835),
    "Ngomongo": (-0.5110, 37.2890)
}

# --- 2. STORAGE & ERROR RECOVERY ---
students_db = {} 
riders_db = []   
pending_requests = [] 

def save_record(filename, entry):
    try:
        with open(filename, "a") as f:
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | {entry}\n")
    except Exception as e:
        print(f"File Write Error: {e}")

def reload_records():
    """Safely reloads data even if files are missing or broken."""
    if os.path.exists("students_records.txt"):
        try:
            with open("students_records.txt", "r") as f:
                for line in f:
                    parts = line.strip().split(" | ")
                    if len(parts) >= 2:
                        data = parts[1].split(":")
                        if len(data) == 2: students_db[data[0].strip()] = data[1].strip()
        except: print("Error reading students_records.txt")
    
    if os.path.exists("riders_records.txt"):
        try:
            with open("riders_records.txt", "r") as f:
                for line in f:
                    parts = line.strip().split(" | ")
                    if len(parts) >= 2:
                        r = parts[1].split(",")
                        if len(r) >= 4:
                            riders_db.append({"name": r[0], "plate": r[1], "id": r[2], "password": r[3], "status": "unavailable"})
        except: print("Error reading riders_records.txt")

# --- 3. AUTH LOGIC ---

@app.route('/auth/signup', methods=['POST'])
def signup():
    data = request.json
    role, name, password = data.get('role'), data.get('name', '').strip(), data.get('password')
    
    if not name or not password:
        return jsonify({"error": "Missing name or password"}), 400

    if role == 'student':
        if name in students_db: return jsonify({"error": "Username taken"}), 400
        students_db[name] = password
        save_record("students_records.txt", f"{name}:{password}")
    else:
        plate, id_num = data.get('plate', '').upper(), str(data.get('id_number', ''))
        if any(r['plate'] == plate or r['id'] == id_num for r in riders_db):
            return jsonify({"error": "Plate or ID already registered"}), 400
        
        new_rider = {"name": name, "plate": plate, "id": id_num, "password": password, "status": "available"}
        riders_db.append(new_rider)
        save_record("riders_records.txt", f"{name},{plate},{id_num},{password}")
    return jsonify({"status": "success"}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    role, name, password = data.get('role'), data.get('name', '').strip(), data.get('password')
    if role == 'student':
        if name in students_db and students_db[name] == password:
            return jsonify({"status": "success"}), 200
    else:
        rider = next((r for r in riders_db if r['name'] == name and r['password'] == password), None)
        if rider:
            rider['status'] = 'available'
            return jsonify({"status": "success", "plate": rider['plate']}), 200
    return jsonify({"error": "Invalid credentials"}), 401

# --- 4. DISPATCH (The 80 Bob Rule) ---

@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json 
    data['time'] = datetime.datetime.now().strftime('%H:%M')
    
    # 80 KES DEFAULT FARE
    fare = 80 
    
    dest_name = data.get('destination')
    u_lat, u_lon = data.get('lat'), data.get('lon')
    dest_coords = KUTUS_LOCATIONS.get(dest_name)
    
    # Check distance: Only increase if it's very far, otherwise stay 80
    if dest_coords and u_lat:
        try:
            dist = geodesic((u_lat, u_lon), dest_coords).km
            if dist > 2.5: # Example: Long distance surcharge
                fare = 120
        except Exception: 
            fare = 80 # Fallback to default if GPS math fails
    
    data['fare'] = fare
    pending_requests.append(data)
    return jsonify({"status": "sent", "fare": fare}), 200

@app.route('/get_requests')
def get_requests():
    rider_plate = request.args.get('plate')
    if not rider_plate: return jsonify([])
    # Direct Dispatch: One student request -> One specific rider
    return jsonify([r for r in pending_requests if r.get('rider_plate') == rider_plate])

# --- 5. SYSTEM STATUS ---

@app.route('/get_active_riders')
def get_active_riders():
    # Only show riders who are currently available
    return jsonify([{"name": r['name'], "plate": r['plate']} for r in riders_db if r['status'] == 'available'])

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    name, status = data.get('name'), data.get('status')
    for r in riders_db:
        if r['name'] == name:
            r['status'] = status
            return jsonify({"status": "success"}), 200
    return jsonify({"error": "Rider not found"}), 404

if __name__ == '__main__':
    reload_records()
    # Runs on port 10000 with Debug mode on for your development
    app.run(host='0.0.0.0', port=10000, debug=True)