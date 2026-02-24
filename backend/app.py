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
MY_COMMISSION = 12

KUTUS_LOCATIONS = {
    "Spenza": (-0.5042, 37.2801), 
    "Diaspora": (-0.5080, 37.2850),
    "School": (-0.5015, 37.2805), 
    "Icon": (-0.5020, 37.2820),
    "Mjini": (-0.5150, 37.2950), 
    "Soko": (-0.5030, 37.2880),
    "Raha Premium": (-0.5065, 37.2835),
    "Ngomongo": (-0.5110, 37.2890)
}

# --- 2. STORAGE ---
students_db = {} 
riders_db = []
student_ride_counts = {}
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
                    if len(data) == 2:
                        students_db[data[0].strip()] = data[1].strip()
    
    if os.path.exists("riders_records.txt"):
        with open("riders_records.txt", "r") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 2:
                    r_data = parts[1].split(",")
                    if len(r_data) == 3:
                        riders_db.append({"name": r_data[0], "plate": r_data[1], "id": r_data[2], "status": "unavailable"})

# --- 3. DARAJA HELPERS ---
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    res = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return res.json().get('access_token')

# --- 4. LIVE STATUS & STATS ---
@app.route('/get_active_riders')
def get_active_riders():
    active_list = [r for r in riders_db if r.get('status') == 'available']
    return jsonify(active_list)

@app.route('/rider_stats')
def rider_stats():
    total_active = len([r for r in riders_db if r.get('status') == 'available'])
    return jsonify({"total_active": total_active})

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    rider_name = data.get('name')
    new_status = data.get('status') 
    for rider in riders_db:
        if rider['name'] == rider_name:
            rider['status'] = new_status
            return jsonify({"status": "success", "current_status": new_status}), 200
    return jsonify({"error": "Rider not found"}), 404

# --- 5. AUTH BLUEPRINTS ---
student_bp = Blueprint('student', __name__)
@student_bp.route('/students/auth', methods=['POST'])
def auth_student():
    data = request.json
    name, password = data.get('name', '').strip(), data.get('password', '')
    if name in students_db:
        if students_db[name] == password:
            return jsonify({"status": "success"}), 200
        return jsonify({"error": "Incorrect password"}), 401
    students_db[name] = password
    save_record("students_records.txt", f"{name}:{password}")
    return jsonify({"status": "success"}), 201

riders_bp = Blueprint('riders', __name__)
@riders_bp.route('/auth', methods=['POST'])
def auth_rider():
    data = request.json
    name, id_num = data.get('name', ''), str(data.get('id_number', ''))
    plate = data.get('plate', '').upper()
    rider_exists = next((r for r in riders_db if r['id'] == id_num), None)
    if rider_exists:
        rider_exists['status'] = 'available'
        return jsonify({"status": "success"}), 200
    if len(name.split()) < 2: return jsonify({"error": "Need Full Names"}), 400
    if not re.match(r"^KM[A-Z]{2}[1-9][0-9]{2}[A-Z]$", plate):
        return jsonify({"error": "Invalid Plate"}), 400
    new_rider = {"name": name, "plate": plate, "id": id_num, "status": "available"}
    riders_db.append(new_rider)
    save_record("riders_records.txt", f"{name},{plate},{id_num}")
    return jsonify({"status": "success"}), 201

# --- 6. PAYMENTS, MAPS & DISPATCH ---

@app.route('/calculate_fare', methods=['POST'])
def fare():
    data = request.json
    dest_name, u_lat, u_lon = data.get('destination'), data.get('lat'), data.get('lon')
    dest_coords = KUTUS_LOCATIONS.get(dest_name)
    if not dest_coords or u_lat is None:
        return jsonify({"total_fare": 50}) 
    dist = geodesic((u_lat, u_lon), dest_coords).km
    final_fare = 70 if dist < 1.2 else 100
    return jsonify({"total_fare": final_fare, "distance": round(dist, 2)})

@app.route('/stk_push', methods=['POST'])
def process_ride_payment():
    data = request.json
    phone, amount, std_name = data.get('phone'), data.get('amount'), data.get('student_name')
    if phone.startswith("0"): phone = "254" + phone[1:]
    
    token = get_access_token()
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    pass_str = DARAJA_SHORTCODE + DARAJA_PASSKEY + timestamp
    password = base64.b64encode(pass_str.encode()).decode()

    payload = {
        "BusinessShortCode": DARAJA_SHORTCODE, "Password": password, "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline", "Amount": amount,
        "PartyA": phone, "PartyB": DARAJA_SHORTCODE, "PhoneNumber": phone,
        "CallBackURL": "https://yourdomain.com/callback",
        "AccountReference": f"Ride_{std_name}", "TransactionDesc": "Kutus Boda Payment"
    }
    res = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                         json=payload, headers={"Authorization": f"Bearer {token}"})
    return jsonify({"mpesa_status": "Prompt Sent"})

@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json # Contains: student, to, fare, rider (plate), lat, lon
    # ADD GOOGLE MAPS LINK: From student GPS to Kutus Destination
    m_url = f"https://www.google.com/maps/dir/?api=1&origin={data['lat']},{data['lon']}&destination=Kutus+{data['to']}&travelmode=motorcycle"
    data['map_link'] = m_url
    data['time'] = datetime.datetime.now().strftime('%H:%M')
    pending_requests.append(data)
    return jsonify({"status": "sent"})

@app.route('/get_requests')
def get_requests():
    return jsonify(pending_requests)

@app.route('/cancel_ride', methods=['POST'])
def cancel_ride():
    std_name = request.json.get('student_name')
    global pending_requests
    pending_requests = [r for r in pending_requests if r.get('student') != std_name]
    return jsonify({"status": "cancelled"})

app.register_blueprint(student_bp)
app.register_blueprint(riders_bp, url_prefix='/riders')

if __name__ == '__main__':
    reload_records()
    app.run(host='0.0.0.0', port=10000)