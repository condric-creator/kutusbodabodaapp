import datetime, os
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.distance import geodesic 

# IMPORT YOUR PAYMENT LOGIC HERE
# Assuming your payment.py has a function called trigger_stk_push
try:
    from payment import trigger_stk_push 
except ImportError:
    print("Warning: payment.py not found. STK push will be disabled.")
    trigger_stk_push = None

app = Flask(__name__)
CORS(app)

KUTUS_LOCATIONS = {
    "SPENZA": (-0.5042, 37.2801), "SCHOOL": (-0.5015, 37.2805), 
    "ICON": (-0.5020, 37.2820), "RAHA": (-0.5065, 37.2835),
    "NGOMONGO": (-0.5110, 37.2890), "DIASPORA": (-0.5080, 37.2850),
    "MJINI": (-0.5150, 37.2950)
}

pending_requests = [] 

@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json
    u_lat, u_lon = data.get('lat'), data.get('lon')
    dest_name = data.get('destination')
    phone = data.get('phone')

    # 1. CALCULATE FARE (Geopy Logic)
    dest_coords = KUTUS_LOCATIONS.get(dest_name)
    fare = 80
    if dest_coords and u_lat:
        distance = geodesic((u_lat, u_lon), dest_coords).km
        if distance > 2.5: fare = 100

    # 2. TRIGGER PAYMENT (Using your payment.py)
    if trigger_stk_push:
        # Pass the phone and the calculated fare to your payment file
        trigger_stk_push(phone, fare)

    # 3. GENERATE NAVIGATION FOR RIDER
    # This creates a real Google Maps link for the rider
    map_url = f"https://www.google.com/maps/dir/?api=1&origin={u_lat},{u_lon}&destination={dest_coords[0]},{dest_coords[1]}&travelmode=driving"
    
    request_entry = {
        "rider_plate": data.get('rider_plate'),
        "destination": dest_name,
        "fare": fare,
        "map_url": map_url,
        "time": datetime.datetime.now().strftime('%H:%M')
    }
    
    pending_requests.append(request_entry)
    return jsonify({"status": "Payment Triggered", "fare": fare}), 200

# Keep your /get_requests and other routes here...
@app.route('/get_requests', methods=['GET'])
def get_requests():
    plate = request.args.get('plate')
    return jsonify([r for r in pending_requests if r['rider_plate'] == plate])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)