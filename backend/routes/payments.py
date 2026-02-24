import requests
from flask import Blueprint, request, jsonify
from datetime import datetime
import base64

payments_bp = Blueprint('payments', __name__)

# 1. --- REAL DARAJA API KEYS ---
CONSUMER_KEY = "Cg4GtJjtJDDvjsO6Fts4A1do7sx91rWMGyu5ktxl5YoxSWEx"
CONSUMER_SECRET = "T4PiebXPp8sRbsOumXR5PcPz4t6utH8kYXCUQcNOlWk7AOo7Xfyegb59WMGccdWf"

# 2. --- BUSINESS CONFIGURATION ---
KCB_PAYBILL = "522522"
KCB_ACCOUNT = "1331585260"
MY_COMMISSION = 12
DARAJA_SHORTCODE = "174379"  # Sandbox Shortcode
DARAJA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

# 3. --- LOYALTY STORAGE (Vouchers) ---
student_ride_counts = {}
rider_ride_counts = {}

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return response.json().get('access_token')

@payments_bp.route('/stk_push', methods=['POST'])
def process_ride_payment():
    data = request.get_json()
    phone = data.get('phone') # Must be 2547XXXXXXXX
    amount = data.get('amount')
    student_name = data.get('student_name')
    rider_id = data.get('rider_id')

    # 4. --- LOGIC: CALCULATE COMMISSION ---
    rider_gets = amount - MY_COMMISSION
    
    # 5. --- LOGIC: UPDATE VOUCHER COUNTS ---
    student_ride_counts[student_name] = student_ride_counts.get(student_name, 0) + 1
    rider_ride_counts[rider_id] = rider_ride_counts.get(rider_id, 0) + 1

    # 6. --- DARAJA STK PUSH TRIGGER ---
    access_token = get_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((DARAJA_SHORTCODE + DARAJA_PASSKEY + timestamp).encode()).decode()

    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "BusinessShortCode": DARAJA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": DARAJA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": "https://mydomain.com/callback",
        "AccountReference": "Kutus Boda APP ",
        "TransactionDesc": "Kutus Boda Payment"
    }

    daraja_res = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload, headers=headers
    )

    # 7. --- RESPONSE MESSAGE ---
    voucher_status = "Keep riding to earn your 200/- voucher!"
    if student_ride_counts[student_name] >= 15:
        voucher_status = "CONGRATS! You've earned a 200/- Student Voucher!"

    return jsonify({
        "mpesa_status": daraja_res.json().get("CustomerMessage", "Request Sent"),
        "kcb_destination": f"Paybill {KCB_PAYBILL} Acc {KCB_ACCOUNT}",
        "commission_report": {
            "your_profit": MY_COMMISSION,
            "rider_balance": rider_gets
        },
        "voucher_info": voucher_status
    }), 200

@payments_bp.route('/weekly_rewards', methods=['GET'])
def get_weekly_winner():
    if not rider_ride_counts:
        return jsonify({"message": "No rides recorded yet"}), 200
    top_rider = max(rider_ride_counts, key=rider_ride_counts.get)
    return jsonify({
        "weekly_top_rider": top_rider,
        "rides_done": rider_ride_counts[top_rider],
        "reward": "300/- Weekly Voucher awarded!"
    }), 200