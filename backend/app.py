import datetime
import requests
import base64
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.distance import geodesic 

app = Flask(__name__)
CORS(app)

# --- DATA STORAGE (RAM) ---
# riders_db stores rider info including ID and Name
riders_db = {}  
# pending_requests stores all active ride calls
pending_requests = [] 

# Kutus GPS Coordinates for Distance Calculation
KUTUS_LOCATIONS = {
    "SPENZA": (-0.5042, 37.2801), "SCHOOL": (-0.5015, 37.2805), 
    "ICON": (-0.5020, 37.2820), "RAHA": (-0.5065, 37.2835),
    "NGOMONGO": (-0.5110, 37.2890), "MJINI": (-0.5150, 37.2950),
    "SOKO": (-0.5120, 37.2910)
}

# Safaricom Daraja API Config
CONSUMER_KEY = "Cg4GtJjtJDDvjsO6Fts4A1do7sx91rWMGyu5ktxl5YoxSWEx"
CONSUMER_SECRET = "T4PiebXPp8sRbsOumXR5PcPz4t6utH8kYXCUQcNOlWk7AOo7Xfyegb59WMGccdWf"
DARAJA_SHORTCODE = "174379"
DARAJA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
CALLBACK_URL = "https://your-ngrok-url.ngrok-free.app/callback"

def get_stk_token():
    try:
        url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        res = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
        return res.json().get('access_token')
    except: 
        return None

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    plate = data.get('plate')
    # Store ID Number and Name for the Rider Portal
    riders_db[plate] = {
        "name": data.get('name'),
        "id_number": data.get('id_number'),
        "plate": plate,
        "status": "available"
    }
    return jsonify({"status": "success"}), 200

@app.route('/get_riders', methods=['GET'])
def get_riders():
    return jsonify(list(riders_db.values())), 200

@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json
    phone = data.get('phone')
    student_name = data.get('student_name') # Captured from frontend
    target_plate = data.get('rider_plate') # The rider the student clicked
    dest_name = data.get('destination')
    s_lat, s_lon = data.get('lat'), data.get('lon')

    # 1. Precise Distance & Fare Calculation
    dest_coords = KUTUS_LOCATIONS.get(dest_name)
    fare = 50
    dist_km = 0
    if dest_coords and s_lat:
        dist_km = round(geodesic((s_lat, s_lon), dest_coords).km, 2)
        # Pricing logic based on distance
        fare = 50 if dist_km < 1.0 else 80 if dist_km < 2.5 else 120

    # 2. M-Pesa STK Push Trigger
    if phone.startswith("0"): phone = "254" + phone[1:]
    token = get_stk_token()
    if token:
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode((DARAJA_SHORTCODE + DARAJA_PASSKEY + timestamp).encode()).decode()
        stk_payload = {
            "BusinessShortCode": DARAJA_SHORTCODE, "Password": password, "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline", "Amount": int(fare), "PartyA": phone,
            "PartyB": DARAJA_SHORTCODE, "PhoneNumber": phone, "CallBackURL": CALLBACK_URL,
            "AccountReference": "KutusBoda", "TransactionDesc": f"Ride for {student_name}"
        }
        requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", 
                      json=stk_payload, headers={"Authorization": f"Bearer {token}"})

    # 3. Get Name of Targeted Rider to show on the Portal
    targeted_rider_name = riders_db.get(target_plate, {}).get('name', target_plate)

    # 4. Save Request (Broadcasted to ALL riders)
    new_req = {
        "student_name": student_name,
        "targeted_rider_name": targeted_rider_name, 
        "target_rider_plate": target_plate,
        "destination": dest_name,
        "fare": fare,
        "distance": dist_km,
        "map_url": f"https://www.google.com/maps/dir/?api=1&origin={s_lat},{s_lon}&destination={dest_coords[0]},{dest_coords[1]}&travelmode=motorcycle",
        "timestamp": datetime.datetime.now().strftime('%H:%M')
    }
    pending_requests.append(new_req)
    return jsonify({"status": "success", "fare": fare, "distance": dist_km}), 200

@app.route('/get_requests', methods=['GET'])
def get_requests():
    # Returns all requests so every rider can see the activity
    return jsonify(pending_requests), 200

if __name__ == '__main__':
    # Use port 10000 for your environment
    app.run(host='0.0.0.0', port=10000, debug=True)