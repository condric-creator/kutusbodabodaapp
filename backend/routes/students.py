from flask import Blueprint, request, jsonify

# Using a Blueprint allows you to plug this into your main app.py easily
student_bp = Blueprint('student', __name__)

# RAM storage for students (if not using the main app's DB)
students_db = {} 

@student_bp.route('/students/register', methods=['POST'])
def register_student():
    """Registers a student with just Name and Password"""
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '')

    if not name or not password:
        return jsonify({"error": "Student Name and Password are required"}), 400

    # Save to RAM
    students_db[name] = password
    return jsonify({
        "status": "Success", 
        "message": f"Welcome to Kutus Elite, {name}!"
    }), 201

@student_bp.route('/students/login', methods=['POST'])
def login_student():
    """Verifies student credentials"""
    data = request.json
    name = data.get('name')
    password = data.get('password')

    if name in students_db and students_db[name] == password:
        return jsonify({"status": "success", "message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid student credentials"}), 401

@student_bp.route('/students/profile', methods=['GET'])
def get_profile():
    """Simple profile check for the 'KEN' display in your UI"""
    name = request.args.get('name')
    if name in students_db:
        return jsonify({"name": name, "role": "Student"})
    return jsonify({"error": "Not found"}), 404