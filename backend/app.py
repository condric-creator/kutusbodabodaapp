import datetime
import requests
import base64
import json
import logging
import random
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash, check_password_hash

# --- 1. INITIALIZATION & LOGGING ---
app = Flask(__name__)
CORS(app)
@app.route('/')
def home():
    return jsonify({"status": "Success", "message": "Kutus Boda Backend is LIVE!"})
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

# --- 2. DATABASE CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kutus_boda_v6.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 3. MODELS ---
class Rider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    id_number = db.Column(db.String(20), unique=True, nullable=False)
    plate_number = db.Column(db.String(15), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="offline") 

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rider_plate = db.Column(db.String(15))
    amount_paid = db.Column(db.Integer) 
    rider_earning = db.Column(db.Integer) 
    admin_profit = db.Column(db.Integer) 
    payment_date = db.Column(db.Date, default=datetime.date.today)

class OTPRecovery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20))
    otp_code = db.Column(db.String(6))
    expiry = db.Column(db.DateTime)

with app.app_context():
    db.create_all()

# --- 4. CONFIG & DESTINATIONS ---
# Using Sandbox credentials for testing
CONSUMER_KEY = "Cg4GtJjtJDDvjsO6Fts4A1do7sx91rWMGyu5ktxl5YoxSWEx"
CONSUMER_SECRET = "T4PiebXPp8sRbsOumXR5PcPz4t6utH8kYXCUQcNOlWk7AOo7Xfyegb59WMGccdWf"
TEST_SHORTCODE = "174379" 
TEST_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

KUTUS_LOCATIONS = {
    "SPENZA": (-0.5762, 37.3060), "SCHOOL": (-0.5660, 37.3203), 
    "ICON": (-0.5568, 37.3333), "RAHA": (-0.5602, 37.3398),
    "NGOMONGO": (-0.5717, 37.3145), "MJINI": (-0.5732, 37.3271),
    "SOKO": (-0.5732, 37.3253), "DIASPORA": (-0.5586, 37.3169)
}

active_requests = {}

# --- 5. UTILITY FUNCTIONS ---

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculates distance in KM using Haversine Formula"""
    R = 6371  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2) * math.sin(d_lat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(d_lon/2) * math.sin(d_lon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_mpesa_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        r = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET), timeout=5)
        return r.json().get('access_token')
    except Exception as e:
        logger.error(f"M-Pesa Token Error: {e}")
        return None

# --- 6. ROUTES ---

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    hashed = generate_password_hash(data['password'])
    try:
        if data['role'] == 'rider':
            new_user = Rider(
                first_name=data['name'], 
                id_number=data['id_number'],
                plate_number=data['plate_number'].upper(), 
                phone_number=data['phone'], 
                password_hash=hashed
            )
        else:
            new_user = Student(
                first_name=data['name'], 
                phone_number=data['phone'], 
                password_hash=hashed
            )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Signup Error: {e}")
        return jsonify({"error": "Phone, Plate, or ID already exists"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    phone = data.get('phone')
    user = Student.query.filter_by(phone_number=phone).first() or \
           Rider.query.filter_by(phone_number=phone).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        role = 'rider' if hasattr(user, 'plate_number') else 'student'
        if role == 'rider':
            user.status = 'online'
            db.session.commit()
            return jsonify({
                "status": "success", 
                "role": "rider", 
                "name": user.first_name, 
                "plate": user.plate_number, 
                "phone": user.phone_number
            })
        return jsonify({
            "status": "success", 
            "role": "student", 
            "name": user.first_name, 
            "phone": user.phone_number
        })
    
    return jsonify({"error": "Invalid phone or password"}), 401

@app.route('/get_riders', methods=['GET'])
def get_riders():
    online_riders = Rider.query.filter_by(status='online').all()
    return jsonify([{"name": r.first_name, "plate": r.plate_number, "status": r.status} for r in online_riders])

@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json
    
    # Format phone for M-Pesa
    raw_phone = str(data.get('phone'))
    if raw_phone.startswith('0'):
        formatted_phone = '254' + raw_phone[1:]
    elif raw_phone.startswith('+'):
        formatted_phone = raw_phone[1:]
    else:
        formatted_phone = raw_phone

    # Distance calculation
    dest_name = data['destination'].upper()
    dest_coords = KUTUS_LOCATIONS.get(dest_name, (-0.5732, 37.3253))
    dist = calculate_distance(float(data['lat']), float(data['lon']), dest_coords[0], dest_coords[1])
    
    # Set fare based on tiers
    if dist < 1.0:
        calculated_fare = 70
    elif dist <= 2.0:
        calculated_fare = 100
    else:
        calculated_fare = 150

    # Trigger M-Pesa STK Push
    token = get_mpesa_token()
    if token:
        ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        pw = base64.b64encode(f"{TEST_SHORTCODE}{TEST_PASSKEY}{ts}".encode()).decode()
        stk_payload = {
            "BusinessShortCode": TEST_SHORTCODE, 
            "Password": pw, "Timestamp": ts,
            "TransactionType": "CustomerPayBillOnline", "Amount": 1, # Sandbox test amount
            "PartyA": formatted_phone, "PartyB": TEST_SHORTCODE, "PhoneNumber": formatted_phone,
            "CallBackURL": "https://your-callback-url.com/api", 
            "AccountReference": "KutusBoda", "TransactionDesc": f"Ride to {dest_name}"
        }
        try:
            res = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", 
                                json=stk_payload, headers={"Authorization": f"Bearer {token}"})
            logger.info(f"M-Pesa API Response: {res.json()}")
        except Exception as e: 
            logger.error(f"STK Push Error: {e}")

    # Generate Map and Request
    req_id = f"R-{random.randint(100,999)}"
    map_url = f"https://www.google.com/maps/dir/?api=1&origin={data['lat']},{data['lon']}&destination={dest_coords[0]},{dest_coords[1]}&travelmode=motorcycle"
    
    active_requests[req_id] = {
        "id": req_id, 
        "student_name": data['student_name'], 
        "phone": formatted_phone, 
        "target_rider_plate": data['rider_plate'], 
        "destination": dest_name,
        "fare": calculated_fare, 
        "map_url": map_url
    }
    return jsonify({"status": "success", "id": req_id, "fare": calculated_fare})

@app.route('/get_requests', methods=['GET'])
def get_requests():
    return jsonify(list(active_requests.values()))

@app.route('/complete_ride', methods=['POST'])
def complete_ride():
    r_id = request.json.get('id')
    if r_id in active_requests:
        req = active_requests[r_id]
        
        # --- 10 BOB COMMISSION LOGIC ---
        total_fare = req['fare']
        admin_profit = 10
        rider_earning = total_fare - admin_profit
        
        new_pay = Payment(
            rider_plate=req['target_rider_plate'], 
            amount_paid=total_fare, 
            rider_earning=rider_earning, 
            admin_profit=admin_profit
        )
        db.session.add(new_pay)
        db.session.commit()
        del active_requests[r_id]
        return jsonify({"status": "completed"})
    return jsonify({"error": "Ride not found"}), 404

@app.route('/get_earnings/<plate>', methods=['GET'])
def get_earnings(plate):
    plate = plate.upper()
    today = datetime.date.today()
    stats = db.session.query(
        func.count(Payment.id), 
        func.sum(Payment.rider_earning)
    ).filter(Payment.rider_plate == plate, Payment.payment_date == today).first()
    
    total_all_time = db.session.query(func.sum(Payment.rider_earning)).filter(Payment.rider_plate == plate).scalar() or 0

    return jsonify({
        "ride_count": stats[0] or 0,
        "daily_earnings": int(stats[1] or 0),
        "total_earnings": int(total_all_time)
    })

@app.route('/request_otp', methods=['POST'])
def request_otp():
    phone = request.json.get('phone')
    otp = str(random.randint(100000, 999999))
    expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
    
    user_exists = Student.query.filter_by(phone_number=phone).first() or \
                  Rider.query.filter_by(phone_number=phone).first()
    
    if not user_exists:
        return jsonify({"error": "Phone number not registered"}), 404

    OTPRecovery.query.filter_by(phone_number=phone).delete()
    db.session.add(OTPRecovery(phone_number=phone, otp_code=otp, expiry=expiry))
    db.session.commit()
    
    print(f"\n[!] SECURITY: OTP for {phone} is {otp}\n")
    return jsonify({"status": "success", "message": "OTP Sent"})

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.json
    phone = data.get('phone')
    otp_code = data.get('otp')
    new_password = data.get('new_password')
    
    entry = OTPRecovery.query.filter_by(phone_number=phone, otp_code=otp_code).first()
    
    if entry and entry.expiry > datetime.datetime.now():
        user = Student.query.filter_by(phone_number=phone).first() or \
               Rider.query.filter_by(phone_number=phone).first()
        
        if user:
            user.password_hash = generate_password_hash(new_password)
            db.session.delete(entry) 
            db.session.commit()
            return jsonify({"status": "success"})
    
    return jsonify({"error": "Invalid or expired OTP"}), 400

if __name__ == "__main__":
    import os
    # If we are on Railway, it will provide a PORT. 
    # If not, we use 10000 and turn on debug mode for local testing.
    port = int(os.environ.get("PORT", 10000))
    is_dev = os.environ.get("PORT") is None # True if on your laptop
    
    app.run(host='0.0.0.0', port=port, debug=is_dev)