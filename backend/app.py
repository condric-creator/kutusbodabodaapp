from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.distance import geodesic
import requests, base64, re, datetime

app = Flask(__name__)
CORS(app)
@app.route('/')
def home():
    return "Kutus Boda Boda App is Live!"

# --- BUSINESS RAM STORAGE ---
riders_db = {} # Format: {"Name": {"id": "...", "plate": "...", "status": "inactive", "has_photo": False}}
student_ride_counts = {}

KUTUS_LOCATIONS = {
    "Spenza": (-0.5042, 37.2801), "Diaspora": (-0.5080, 37.2850),
    "School": (-0.5015, 37.2805), "Icon": (-0.5020, 37.2820),
    "Mjini": (-0.5150, 37.2950), "Soko": (-0.5030, 37.2880)
}

# Daraja Sandbox Keys
CONSUMER_KEY = "Cg4GtJjtJDDvjsO6Fts4A1do7sx91rWMGyu5ktxl5YoxSWEx"
CONSUMER_SECRET = "T4PiebXPp8sRbsOumXR5PcPz4t6utH8kYXCUQcNOlWk7AOo7Xfyegb59WMGccdWf"
DARAJA_SHORTCODE = "174379"
DARAJA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    res = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return res.json().get('access_token')

@app.route('/auth/student', methods=['POST'])
def auth_student():
    return jsonify({"status": "Success"}), 200

@app.route('/riders/register', methods=['POST'])
def register_rider():
    data = request.json
    name = data.get('name', '').strip()
    id_num = data.get('id_number', '').strip()
    
    # Validation
    if len(name.split()) != 3:
        return jsonify({"error": "Exactly 3 names required"}), 400
    if not id_num:
        return jsonify({"error": "ID Number is required"}), 400
        
    riders_db[name] = {
        "id": id_num, 
        "plate": data.get('plate'), 
        "status": "inactive", 
        "has_photo": False
    }
    return jsonify({"status": "Success"}), 201

@app.route('/rider/update_status', methods=['POST'])
def update_status():
    data = request.json
    name = data.get('name')
    if name in riders_db:
        riders_db[name]['status'] = data.get('status')
        riders_db[name]['has_photo'] = data.get('has_photo')
        return jsonify({"status": "Updated"}), 200
    return jsonify({"error": "Rider not found"}), 404

@app.route('/check_riders', methods=['GET'])
def check_riders():
    # Only show available if rider is 'available' AND has photo
    active = [n for n, d in riders_db.items() if d['status'] == 'available' and d['has_photo']]
    return jsonify({"available": len(active) > 0})

@app.route('/calculate_fare', methods=['POST'])
def calculate():
    data = request.json
    dist = geodesic((data['lat'], data['lon']), KUTUS_LOCATIONS[data['destination']]).km
    fare = 75 if dist < 1 else 100
    return jsonify({"distance": round(dist, 2), "total_fare": fare})

@app.route('/stk_push', methods=['POST'])
def pay():
    data = request.json
    token = get_access_token()
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((DARAJA_SHORTCODE + DARAJA_PASSKEY + timestamp).encode()).decode()
    payload = {
        "BusinessShortCode": DARAJA_SHORTCODE, "Password": password, "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline", "Amount": data.get('amount'),
        "PartyA": data.get('phone'), "PartyB": DARAJA_SHORTCODE, "PhoneNumber": data.get('phone'),
        "CallBackURL": "https://mydomain.com/callback",
        "AccountReference": "KutusBoda", "TransactionDesc": "Ride"
    }
    requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", json=payload, headers={"Authorization": f"Bearer {token}"})
    return jsonify({"status": "Request Sent"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)