from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)

users = {}

def create_user(username, password, sponsor_id=None, is_admin=False):
    user_id = str(uuid.uuid4())
    user = {
        "user_id": user_id,
        "username": username,
        "password": password,  # For demo ONLY; not secure for real project!
        "sponsor_id": sponsor_id,
        "directs": [],
        "power_leg": None,
        "other_leg": [],
        "is_admin": is_admin
    }
    users[user_id] = user
    return user

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data['username']
    password = data['password']
    sponsor_id = data.get('sponsor_id')
    if sponsor_id and len(users[sponsor_id]['directs']) >= 12:
        return jsonify({"message": "Sponsor already has 12 direct referrals"}), 400
    u = create_user(username, password, sponsor_id)
    if sponsor_id:
        spnsr = users[sponsor_id]
        spnsr['directs'].append(u["user_id"])
        if not spnsr['power_leg']:
            spnsr['power_leg'] = u["user_id"]
        else:
            spnsr['other_leg'].append(u["user_id"])
    return jsonify({"user_id": u["user_id"]})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    for uid, u in users.items():
        if u["username"] == data.get('username') and u["password"] == data.get('password'):
            return jsonify({"user_id": uid, "username": u["username"], "is_admin": u["is_admin"]}), 200
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/user/<user_id>/panel', methods=['GET'])
def user_panel(user_id):
    user = users.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    return jsonify(user)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    for uid, u in users.items():
        if u["username"] == data.get('username') and u["password"] == data.get('password') and u["is_admin"]:
            return jsonify({"user_id": uid, "username": u["username"], "is_admin": True}), 200
    return jsonify({"message": "Invalid admin login"}), 401

@app.route('/admin/<admin_id>/all_users', methods=['GET'])
def admin_panel(admin_id):
    user = users.get(admin_id)
    if not user or not user["is_admin"]:
        return jsonify({"message": "Admin not found"}), 404
    return jsonify(list(users.values()))

if __name__ == "__main__":
    app.run()
