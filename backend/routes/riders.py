from flask import Blueprint, request, jsonify
import re

riders_bp = Blueprint('riders', __name__)

# Temporary RAM storage
riders_db = []

def validate_plate(plate):
    pattern = r"^KM[A-Z]{2}[1-9][0-9]{2}[A-Z]$"
    return bool(re.match(pattern, plate))

@riders_bp.route('/register', methods=['POST'])
def register_rider():
    data = request.get_json()
    full_name = data.get('name', '')
    id_number = str(data.get('id_number', ''))
    plate = data.get('plate', '').upper()

    if len(full_name.strip().split()) != 3:
        return jsonify({"error": "You must provide exactly 3 names"}), 400

    if not id_number.isdigit() or len(id_number) > 9:
        return jsonify({"error": "ID number must be digits only (max 9)"}), 400

    if not validate_plate(plate):
        return jsonify({"error": "Invalid Plate! Use format KMGS567M"}), 400

    # New: Add 'status' set to 'available' by default
    new_rider = {
        "name": full_name,
        "plate": plate,
        "id": id_number,
        "status": "available" 
    }
    
    riders_db.append(new_rider)

    return jsonify({
        "status": "Success",
        "rider": new_rider,
        "message": "you have been registered to kutus bodaboda app!"
    }), 201

# New Route: To let the rider switch between Available and Unavailable
@riders_bp.route('/toggle_status/<id_num>', methods=['PATCH'])
def toggle_status(id_num):
    for rider in riders_db:
        if rider['id'] == id_num:
            # If available -> make unavailable, and vice versa
            rider['status'] = "unavailable" if rider['status'] == "available" else "available"
            return jsonify({"message": f"Status is now {rider['status']}", "rider": rider}), 200
    
    return jsonify({"error": "Rider not found"}), 404