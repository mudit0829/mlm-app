from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import uuid
import os

app = Flask(__name__, template_folder='templates')
CORS(app)

users = {}

# TradeEra initial admin user (for test login)
admin_user = {
    "user_id": "admin-1",
    "username": "admin",
    "password": "admin123",   # Change as needed
    "sponsor_id": None,
    "directs": [],
    "power_leg": None,
    "other_leg": [],
    "is_admin": True,
    "email": "",
    "first_name": "",
    "last_name": "",
    "dob": "",
    "country": "",
    "mobile": "",
    "state": "",
    "position": ""
}
users[admin_user["user_id"]] = admin_user

def create_user(data):
    user_id = str(uuid.uuid4())
    user = {
        "user_id": user_id,
        "username": data['username'],
        "password": data['password'],
        "sponsor_id": data['referral_code'],
        "directs": [],
        "power_leg": None,
        "other_leg": [],
        "is_admin": False,
        "email": data['email'],
        "first_name": data['first_name'],
        "last_name": data['last_name'],
        "dob": data['dob'],
        "country": data['country'],
        "mobile": data['mobile'],
        "state": data['state'],
        "position": data['position']
    }
    users[user_id] = user
    # Binary logic: placement left/right
    sponsor_id = data['referral_code']
    if sponsor_id:
        sponsor = users.get(sponsor_id)
        if not sponsor:
            return None, "Referral code not found"
        if data['position'] == "LEFT":
            # Limit 6 on left: if directs under sponsor's power leg <6, add to left/power_leg
            left_count = sum(
                1 for uid in sponsor['directs'] 
                if users[uid]['position'] == 'LEFT'
            )
            if left_count >= 6:
                return None, "Left position filled under this sponsor"
            sponsor['directs'].append(user_id)
            if not sponsor['power_leg'] or sponsor['power_leg'] == user_id:
                sponsor['power_leg'] = user_id
        else:  # RIGHT
            right_count = sum(
                1 for uid in sponsor['directs'] 
                if users[uid]['position'] == 'RIGHT'
            )
            if right_count >= 6:
                return None, "Right position filled under this sponsor"
            sponsor['directs'].append(user_id)
            sponsor['other_leg'].append(user_id)
    return user, None

@app.route('/', methods=['GET'])
def home():
    return render_template('login.html')

@app.route('/signup-page', methods=['GET'])
def signup_page():
    return render_template('signup.html')

@app.route('/user-panel', methods=['GET'])
def user_panel_page():
    return render_template('user_panel.html')

@app.route('/admin-panel', methods=['GET'])
def admin_panel_page():
    return render_template('admin_panel.html')

# User registration endpoint
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    required_fields = ['username', 'password', 'referral_code', 'position', 'first_name', 'last_name', 'email', 'dob', 'country', 'mobile', 'state']
    for f in required_fields:
        if not data.get(f):
            return jsonify({'message': f'Missing {f}'}), 400
    user, error = create_user(data)
    if error:
        return jsonify({'message': error}), 400
    return jsonify({"user_id": user["user_id"]})

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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
