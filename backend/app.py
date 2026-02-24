import datetime, os
from flask import Flask, request, jsonify
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

# --- 2. STORAGE ---
students_db = {} 
riders_db = []   
pending_requests = [] 

# --- 3. DATA PERSISTENCE ---
def save_record(filename, entry):
    try:
        with open(filename, "a") as f:
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | {entry}\n")
    except Exception as e:
        print(f"Write Error: {e}")

def reload_records():
    if os.path.exists("students_records.txt"):
        with open("students_records.txt", "r") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 2:
                    data = parts[1].split(":")
                    if len(data) == 2: students_db[data[0]] = data[1]
    
    if os.path.exists("riders_records.txt"):
        with open("riders_records.txt", "r") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 2:
                    r = parts[1].split(",")
                    if len(r) >= 4:
                        riders_db.append({
                            "name": r[0], "plate": r[1], "id": r[2], 
                            "password": r[3], "status": "unavailable"
                        })

# --- 4. ADVANCED LOGIC ---
def calculate_fare(u_lat, u_lon, dest_name):
    base_fare = 80
    max_fare = 100
    dest_coords = KUTUS_LOCATIONS.get(dest_name)
    if not dest_coords or u_lat is None: return base_fare
    try:
        dist = geodesic((u_lat, u_lon), dest_coords).km
        return max_fare if dist > 2.5 else base_fare
    except: return base_fare

# --- 5. ENHANCED API ENDPOINTS ---

@app.route('/auth/signup', methods=['POST'])
def signup():
    data = request.json
    role, name, password = data.get('role'), data.get('name', '').strip(), data.get('password')
    if role == 'student':
        if name in students_db: return jsonify({"error": "Name taken"}), 400
        students_db[name] = password
        save_record("students_records.txt", f"{name}:{password}")
    else:
        plate, id_num = data.get('plate', '').upper(), data.get('id_number')
        if any(r['plate'] == plate for r in riders_db):
            return jsonify({"error": "Plate already registered"}), 400
        riders_db.append({"name": name, "plate": plate, "id": id_num, "password": password, "status": "available"})
        save_record("riders_records.txt", f"{name},{plate},{id_num},{password}")
    return jsonify({"status": "success"}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    role, name, password = data.get('role'), data.get('name', '').strip(), data.get('password')
    if role == 'student':
        if students_db.get(name) == password: return jsonify({"status": "success"}), 200
    else:
        rider = next((r for r in riders_db if r['name'] == name and r['password'] == password), None)
        if rider:
            rider['status'] = 'available' # Auto-online on login
            return jsonify({"status": "success", "plate": rider['plate']}), 200
    return jsonify({"error": "Invalid login"}), 401

@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json
    # Validation: Must have a destination and a rider selected
    if not data.get('destination') or not data.get('rider_plate'):
        return jsonify({"error": "Missing destination or rider"}), 400

    data['fare'] = calculate_fare(data.get('lat'), data.get('lon'), data.get('destination'))
    data['time'] = datetime.datetime.now().strftime('%H:%M')
    data['id'] = f"REQ-{datetime.datetime.now().strftime('%f')}" # Unique ID for completion
    
    if len(pending_requests) > 50: pending_requests.pop(0) # RAM Reset
    pending_requests.append(data)
    return jsonify({"status": "sent", "fare": data['fare']}), 200

@app.route('/complete_request', methods=['POST'])
def complete_request():
    """Removes the request from the rider's screen after drop-off."""
    req_id = request.json.get('request_id')
    global pending_requests
    pending_requests = [r for r in pending_requests if r.get('id') != req_id]
    return jsonify({"status": "success"}), 200

@app.route('/get_requests')
def get_requests():
    plate = request.args.get('plate')
    return jsonify([r for r in pending_requests if r.get('rider_plate') == plate])

@app.route('/get_active_riders')
def get_active_riders():
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
    app.run(host='0.0.0.0', port=10000, debug=True)