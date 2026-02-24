import datetime, os
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.distance import geodesic 

app = Flask(__name__)
CORS(app)

# --- 1. CONFIGURATION ---
KUTUS_LOCATIONS = {
    "SPENZA": (-0.5042, 37.2801), 
    "SCHOOL": (-0.5015, 37.2805), 
    "ICON": (-0.5020, 37.2820),
    "RAHA": (-0.5065, 37.2835),
    "NGOMONGO": (-0.5110, 37.2890)
}

# --- 2. STORAGE ---
students_db = {} 
riders_db = []   
pending_requests = [] 

# --- 3. PERSISTENCE (Existing logic) ---
def save_record(filename, entry):
    with open(filename, "a") as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | {entry}\n")

# --- 4. THE LOGIC (Rules Implementation) ---

@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json
    
    # RULE: Must have destination, rider, and PHONE NUMBER (Payment)
    if not data.get('destination') or not data.get('rider_plate') or not data.get('phone'):
        return jsonify({"error": "No confirmation: Missing info"}), 400

    # Capture location from frontend
    u_lat = data.get('lat')
    u_lon = data.get('lon')
    dest_name = data.get('destination')
    
    # Generate Google Maps Link: From Student Lat/Lon to Destination
    dest_coords = KUTUS_LOCATIONS.get(dest_name, (0,0))
    map_url = f"https://www.google.com/maps/dir/{u_lat},{u_lon}/{dest_coords[0]},{dest_coords[1]}"
    
    request_entry = {
        "id": f"REQ-{datetime.datetime.now().strftime('%f')}",
        "phone": data.get('phone'),
        "rider_plate": data.get('rider_plate'),
        "destination": dest_name,
        "map_url": map_url,
        "status": "pending",
        "time": datetime.datetime.now().strftime('%H:%M')
    }
    
    pending_requests.append(request_entry)
    return jsonify({"status": "sent", "request_id": request_entry['id']}), 200

@app.route('/get_requests', methods=['GET'])
def get_requests():
    plate = request.args.get('plate')
    # RULE: Only return requests for the specific rider if they are active
    return jsonify([r for r in pending_requests if r['rider_plate'] == plate])

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    # Logic to toggle rider availability
    for r in riders_db:
        if r['plate'] == data.get('plate'):
            r['status'] = data.get('status') # 'available' or 'unavailable'
            return jsonify({"status": "updated"}), 200
    return jsonify({"error": "Not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)