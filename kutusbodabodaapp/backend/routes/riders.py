from flask import Blueprint, request, jsonify
import re

riders_bp = Blueprint('riders', __name__)

def validate_plate(plate):
    # Pattern: KM + 2 letters + 3 numbers (not 0) + 1 letter (Example: KMGS567M)
    pattern = r"^KM[A-Z]{2}[1-9][0-9]{2}[A-Z]$"
    return bool(re.match(pattern, plate))

@riders_bp.route('/register', methods=['POST'])
def register_rider():
    data = request.get_json()
    
    full_name = data.get('name', '')
    id_number = str(data.get('id_number', ''))
    plate = data.get('plate', '').upper()

    # 1. Check for exactly 3 names
    name_parts = full_name.strip().split()
    if len(name_parts) != 3:
        return jsonify({"error": "You must provide exactly 3 names (First, Middle, Last)"}), 400

    # 2. Check ID length (not more than 9 digits)
    if not id_number.isdigit() or len(id_number) > 9:
        return jsonify({"error": "ID number must be digits only and not more than 9 characters"}), 400

    # 3. Check Plate format
    if not validate_plate(plate):
        return jsonify({"error": "Invalid Plate! Use format KMGS567M (Numbers cannot start with 0)"}), 400

    # If all checks pass:
    return jsonify({
        "status": "Success",
        "rider": {
            "name": full_name,
            "plate": plate,
            "id": id_number
        },
        "message": "you have been regirested to kutus bodaboda app!"
    }), 201
@riders_bp.route('/list', methods=['GET'])
def get_riders():
    # This sends back the list of all riders we have stored in RAM
    return jsonify({
        "total_riders": len(riders_db),
        "riders": riders_db
    }), 200    
