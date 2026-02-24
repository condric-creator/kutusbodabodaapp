import base64
import datetime
import requests
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.distance import geodesic

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
CONSUMER_KEY = "Cg4GtJjtJDDvjsO6Fts4A1do7sx91rWMGyu5ktxl5YoxSWEx"
CONSUMER_SECRET = "T4PiebXPp8sRbsOumXR5PcPz4t6utH8kYXCUQcNOlWk7AOo7Xfyegb59WMGccdWf"
DARAJA_SHORTCODE = "174379"
DARAJA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

# --- BUSINESS RAM STORAGE ---
riders_db = {} 
KUTUS_LOCATIONS = {
    "Spenza": (-0.5042, 37.2801), "Diaspora": (-0.5080, 37.2850),
    "School": (-0.5015, 37.2805), "Icon": (-0.5020, 37.2820),
    "Mjini": (-0.5150, 37.2950), "Soko": (-0.5030, 37.2880)
}

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        res = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET), timeout=10)
        return res.json().get('access_token')
    except Exception as e:
        return None

def format_phone_number(phone):
    phone = str(phone).strip().replace("+", "")
    if phone.startswith("0"):
        return "254" + phone[1:]
    return phone

@app.route('/')
def home():
    return "Kutus Boda Boda App is Live!"

@app.route('/stk_push', methods=['POST'])
def pay():
    data = request.json
    phone = format_phone_number(data.get('phone'))
    amount = data.get('amount')
    
    token = get_access_token()
    if not token:
        return jsonify({"error": "Payment gateway down"}), 503

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = DARAJA_SHORTCODE + DARAJA_PASSKEY + timestamp
    password = base64.b64encode(password_str.encode()).decode()
    
    # This is where we make it "Beautiful" for the user
    # Note: Description is limited to 13-20 characters on some phone screens
    payload = {
        "BusinessShortCode": DARAJA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone, 
        "PartyB": DARAJA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": "https://yourdomain.com/callback", 
        "AccountReference": "KutusBoda",
        "TransactionDesc": "Pay for ride with Kutus Boda App" # Custom message here
    }
    
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    res = requests.post(api_url, json=payload, headers={"Authorization": f"Bearer {token}"})
    return jsonify(res.json())

# --- REMAINING API ENDPOINTS ---
@app.route('/riders/register', methods=['POST'])
def register_rider():
    data = request.json
    name = data.get('name', '').strip()
    if len(name.split()) != 3:
        return jsonify({"error": "Exactly 3 names required"}), 400
    riders_db[name] = {"id": data.get('id_number'), "status": "inactive"}
    return jsonify({"status": "Success"}), 201

@app.route('/calculate_fare', methods=['POST'])
def calculate():
    data = request.json
    dest_coords = KUTUS_LOCATIONS.get(data['destination'])
    dist = geodesic((data['lat'], data['lon']), dest_coords).km
    fare = 75 if dist < 1 else 100
    return jsonify({"distance_km": round(dist, 2), "total_fare": fare})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)