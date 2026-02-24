import base64
import datetime
import requests
import os
import re
from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from geopy.distance import geodesic

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
CONSUMER_KEY = "Cg4GtJjtJDDvjsO6Fts4A1do7sx91rWMGyu5ktxl5YoxSWEx"
CONSUMER_SECRET = "T4PiebXPp8sRbsOumXR5PcPz4t6utH8kYXCUQcNOlWk7AOo7Xfyegb59WMGccdWf"
DARAJA_SHORTCODE = "174379"
DARAJA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
MY_COMMISSION = 12

KUTUS_LOCATIONS = {
    "Spenza": (-0.5042, 37.2801), "Diaspora": (-0.5080, 37.2850),
    "School": (-0.5015, 37.2805), "Icon": (-0.5020, 37.2820),
    "Mjini": (-0.5150, 37.2950), "Soko": (-0.5030, 37.2880)
}

# --- DATABASES (RAM Storage) ---
students_db = {} 
riders_db = []
student_ride_counts = {}
rider_ride_counts = {}

# --- HELPER: M-PESA TOKEN ---
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    res = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return res.json().get('access_token')

# --- BLUEPRINT: STUDENTS ---
student_bp = Blueprint('student', __name__)
@student_bp.route('/students/register', methods=['POST'])
def reg_std():
    data = request.json
    name, password = data.get('name', '').strip(), data.get('password', '')
    if not name or not password: return jsonify({"error": "Missing credentials"}), 400
    students_db[name] = password
    return jsonify({"status": "Success"}), 201

@student_bp.route('/students/login', methods=['POST'])
def login_std():
    data = request.json
    if students_db.get(data.get('name')) == data.get('password'):
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Invalid login"}), 401

# --- BLUEPRINT: RIDERS ---
riders_bp = Blueprint('riders', __name__)
@riders_bp.route('/register', methods=['POST'])
def reg_rid():
    data = request.json
    name, plate = data.get('name', ''), data.get('plate', '').upper()
    if len(name.split()) != 3: return jsonify({"error": "Need 3 names"}), 400
    if not re.match(r"^KM[A-Z]{2}[1-9][0-9]{2}[A-Z]$", plate):
        return jsonify({"error": "Invalid Plate (Format: KMGS567M)"}), 400
    new_rider = {"name": name, "plate": plate, "id": data.get('id_number'), "status": "available"}
    riders_db.append(new_rider)
    return jsonify({"status": "Success"}), 201

# --- BLUEPRINT: PAYMENTS & LOYALTY ---
pay_bp = Blueprint('payments', __name__)
@pay_bp.route('/stk_push', methods=['POST'])
def process_pay():
    data = request.json
    phone, amount = data.get('phone'), data.get('amount')
    std_name, rid_id = data.get('student_name'), data.get('rider_id')
    
    student_ride_counts[std_name] = student_ride_counts.get(std_name, 0) + 1
    rider_ride_counts[rid_id] = rider_ride_counts.get(rid_id, 0) + 1
    
    token = get_access_token()
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    pass_str = DARAJA_SHORTCODE + DARAJA_PASSKEY + timestamp
    password = base64.b64encode(pass_str.encode()).decode()
    
    payload = {
        "BusinessShortCode": DARAJA_SHORTCODE, "Password": password, "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline", "Amount": amount,
        "PartyA": phone, "PartyB": DARAJA_SHORTCODE, "PhoneNumber": phone,
        "CallBackURL": "https://yourdomain.com/callback",
        "AccountReference": f"Ride_{std_name}", "TransactionDesc": "Pay for ride with Kutus Boda App"
    }
    res = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", 
                        json=payload, headers={"Authorization": f"Bearer {token}"})
    
    v_msg = "Keep riding for a 200/- voucher!"
    if student_ride_counts.get(std_name, 0) >= 15: v_msg = "CONGRATS! 200/- Voucher Earned!"
    
    return jsonify({"mpesa_status": "Prompt Sent", "voucher_info": v_msg})

# --- MAIN APP ROUTES ---
@app.route('/calculate_fare', methods=['POST'])
def fare():
    data = request.json
    dest = KUTUS_LOCATIONS.get(data.get('destination'))
    dist = geodesic((data.get('lat'), data.get('lon')), dest).km
    return jsonify({"total_fare": 75 if dist < 1 else 100})

@app.route('/check_riders')
def check():
    available = any(r['status'] == 'available' for r in riders_db)
    return jsonify({"available": available})

app.register_blueprint(student_bp)
app.register_blueprint(riders_bp, url_prefix='/riders')
app.register_blueprint(pay_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)