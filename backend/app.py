import datetime, os, requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.distance import geodesic 
from base64 import b64encode

app = Flask(__name__)
CORS(app)

# --- 1. CONFIGURATION (All Locations Included) ---
KUTUS_LOCATIONS = {
    "SPENZA": (-0.5042, 37.2801), 
    "SCHOOL": (-0.5015, 37.2805), 
    "ICON": (-0.5020, 37.2820),
    "RAHA": (-0.5065, 37.2835),
    "NGOMONGO": (-0.5110, 37.2890),
    "DIASPORA": (-0.5080, 37.2850),
    "MJINI": (-0.5150, 37.2950)
}

# Safaricom Sandbox Credentials
CONSUMER_KEY = "YOUR_KEY"
CONSUMER_SECRET = "YOUR_SECRET"
SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

pending_requests = [] 

# --- 2. THE LOGIC ---

def get_stk_token():
    res = requests.get("https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
                       auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return res.json().get('access_token')

@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json
    u_lat = data.get('lat')
    u_lon = data.get('lon')
    dest_name = data.get('destination')
    phone = data.get('phone')

    if not all([dest_name, data.get('rider_plate'), phone]):
        return jsonify({"error": "Missing information"}), 400

    # GEOPY LOGIC: Calculate Distance & Fare
    dest_coords = KUTUS_LOCATIONS.get(dest_name)
    fare = 80 # Default base fare
    if dest_coords and u_lat:
        distance = geodesic((u_lat, u_lon), dest_coords).km
        # If ride is more than 2.5km, charge 100/-
        if distance > 2.5:
            fare = 100

    # STK PUSH LOGIC
    token = get_stk_token()
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    password = b64encode((SHORTCODE + PASSKEY + timestamp).encode()).decode()
    
    stk_payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": fare, # Calculated dynamic fare
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": "https://yourdomain.com/callback",
        "AccountReference": f"RideTo{dest_name}",
        "TransactionDesc": "Kutus Boda Payment"
    }

    # Generate Map Link for the Rider
    map_url = f"https://www.google.com/maps/dir/{u_lat},{u_lon}/{dest_coords[0]},{dest_coords[1]}"
    
    request_entry = {
        "id": f"REQ-{datetime.datetime.now().strftime('%f')}",
        "phone": phone,
        "rider_plate": data.get('rider_plate'),
        "destination": dest_name,
        "fare": fare,
        "map_url": map_url,
        "time": datetime.datetime.now().strftime('%H:%M')
    }
    
    # Send STK Push to Safaricom
    headers = {"Authorization": f"Bearer {token}"}
    requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", 
                  json=stk_payload, headers=headers)

    pending_requests.append(request_entry)
    return jsonify({"status": "sent", "fare": fare}), 200

@app.route('/get_requests', methods=['GET'])
def get_requests():
    plate = request.args.get('plate')
    return jsonify([r for r in pending_requests if r['rider_plate'] == plate])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)