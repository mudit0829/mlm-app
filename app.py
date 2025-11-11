from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import uuid
import os
import json
from datetime import datetime

app = Flask(__name__, template_folder='templates')
CORS(app)

app.config['SECRET_KEY'] = 'mlm-app-secret-key-2025'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# ===== FILE-BASED DATABASE =====
DB_FILE = "users_database.json"
MAX_DIRECTS = 12
ACTIVATION_COST = 100

# ===== LEVEL INCOME (Activation Wallet) =====
LEVEL_INCOME = {
    1: 10.00, 2: 5.00, 3: 3.00, 4: 2.00,
    5: 1.00, 6: 1.00, 7: 1.00, 8: 1.00, 9: 1.00, 10: 1.00, 11: 1.00,
    12: 0.50, 13: 0.50, 14: 0.50, 15: 0.50, 16: 0.50, 17: 0.50, 18: 0.50, 19: 0.50, 20: 0.50,
    21: 0.25, 22: 0.25, 23: 0.25, 24: 0.25, 25: 0.25, 26: 0.25, 27: 0.25, 28: 0.25, 29: 0.25, 30: 0.25
}

# ===== DIRECT REQUIREMENTS TO UNLOCK LEVEL INCOME =====
DIRECT_REQUIREMENTS = {
    1: 0, 2: 2, 3: 4,
    4: 6, 5: 6, 6: 6, 7: 6, 8: 6, 9: 6, 10: 6,
    11: 8, 12: 8, 13: 8, 14: 8, 15: 8, 16: 8, 17: 8, 18: 8, 19: 8, 20: 8,
    21: 12, 22: 12, 23: 12, 24: 12, 25: 12, 26: 12, 27: 12, 28: 12, 29: 12, 30: 12
}

# ===== MATCHING INCOME =====
MATCHING_PER_PAIR = 10.00

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(db):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(db, f, indent=2, default=str)
        print(f"💾 Database saved to {DB_FILE}")
    except Exception as e:
        print(f"Error saving database: {e}")

users_db = load_db()

# Admin user
ADMIN_USER = {
    "user_id": "admin-1",
    "username": "admin",
    "password": "admin123",
    "email": "admin@tradeera.com",
    "first_name": "Admin",
    "last_name": "User",
    "is_admin": True,
    "status": "active",
    "activation_status": "active",
    "activation_date": datetime.now().isoformat(),
    "created_at": datetime.now().isoformat(),
    "wallet_balance": 0,
    "activation_wallet": 0,
    "matching_wallet": 0,
    "referral_code": "ADMIN123",
    "sponsor_id": None,
    "direct_referrals": [],
    "power_leg_user": None,
    "other_leg_users": [],
    "matched_pairs": 0,
    "total_income": 0,
    "commission_received": 0,
    "phone": "",
    "country": "India",
    "state": "",
    "dob": "",
    "income_history": []
}

if "admin-1" not in users_db:
    users_db["admin-1"] = ADMIN_USER
    save_db(users_db)

def generate_referral_code():
    return str(uuid.uuid4())[:8].upper()

def count_team(user_id, db):
    count = 1
    user = db.get(user_id)
    if not user:
        return 0
    for direct_id in user.get('direct_referrals', []):
        count += count_team(direct_id, db)
    return count

def calculate_power_leg(user_id, db):
    user = db.get(user_id)
    if not user:
        return {'power_leg': 0, 'other_leg': 0}
    directs = user.get('direct_referrals', [])
    if len(directs) == 0:
        return {'power_leg': 0, 'other_leg': 0}
    power_leg_user_id = directs[0]
    power_leg_count = count_team(power_leg_user_id, db)
    other_leg_count = sum(count_team(direct_id, db) for direct_id in directs[1:])
    return {
        'power_leg': power_leg_count,
        'other_leg': other_leg_count,
        'power_leg_user': power_leg_user_id
    }

def distribute_activation_income(user_id, db):
    user = db.get(user_id)
    if not user or not user.get('sponsor_id'):
        return
    current_sponsor_id = user.get('sponsor_id')
    level = 1
    while current_sponsor_id and level <= 30:
        sponsor = db.get(current_sponsor_id)
        if not sponsor:
            break
        if sponsor.get('activation_status') != 'active':
            current_sponsor_id = sponsor.get('sponsor_id')
            level += 1
            continue
        sponsor_directs = len(sponsor.get('direct_referrals', []))
        required_directs = DIRECT_REQUIREMENTS.get(level, 12)
        if sponsor_directs >= required_directs:
            income = LEVEL_INCOME.get(level, 0)
            sponsor['activation_wallet'] = sponsor.get('activation_wallet', 0) + income
            sponsor['total_income'] = sponsor.get('total_income', 0) + income
            if 'income_history' not in sponsor:
                sponsor['income_history'] = []
            sponsor['income_history'].append({
                'type': 'activation_wallet',
                'from_user': user_id,
                'level': level,
                'amount': income,
                'date': datetime.now().isoformat()
            })
        current_sponsor_id = sponsor.get('sponsor_id')
        level += 1

def calculate_matching_income(user_id, db):
    user = db.get(user_id)
    if not user or user.get('activation_status') != 'active':
        return
    leg_data = calculate_power_leg(user_id, db)
    power_leg = leg_data['power_leg']
    other_leg = leg_data['other_leg']
    new_matching = min(power_leg, other_leg)
    old_matching = user.get('matched_pairs', 0)
    if new_matching > old_matching:
        pairs_increment = new_matching - old_matching
        income = pairs_increment * MATCHING_PER_PAIR
        user['matching_wallet'] = user.get('matching_wallet', 0) + income
        user['total_income'] = user.get('total_income', 0) + income
        user['matched_pairs'] = new_matching
        if 'income_history' not in user:
            user['income_history'] = []
        user['income_history'].append({
            'type': 'matching_wallet',
            'pairs': pairs_increment,
            'amount': income,
            'date': datetime.now().isoformat()
        })

def create_user(data):
    user_id = str(uuid.uuid4())
    referral_code = generate_referral_code()
    sponsor_code = data.get('referral_code')
    sponsor_user_id = None
    for uid, u in users_db.items():
        if u.get('referral_code') == sponsor_code:
            sponsor_user_id = uid
            break
    if not sponsor_user_id:
        return None, "Invalid Referral Code"
    sponsor = users_db[sponsor_user_id]
    if len(sponsor.get('direct_referrals', [])) >= MAX_DIRECTS:
        return None, f"Sponsor has reached maximum limit of {MAX_DIRECTS} direct members. Cannot add more."
    if any(u['username'].lower() == data['username'].lower() for u in users_db.values()):
        return None, "Username already exists"
    if any(u['email'].lower() == data['email'].lower() for u in users_db.values()):
        return None, "Email already registered"
    user = {
        "user_id": user_id,
        "username": data['username'],
        "password": data['password'],
        "email": data['email'],
        "first_name": data['first_name'],
        "last_name": data['last_name'],
        "dob": data.get('dob', ''),
        "country": data.get('country', ''),
        "mobile": data.get('mobile', ''),
        "state": data.get('state', ''),
        "country_code": data.get('country_code', ''),
        "is_admin": False,
        "status": "active",
        "activation_status": "inactive",
        "activation_date": None,
        "activation_cost": ACTIVATION_COST,
        "created_at": datetime.now().isoformat(),
        "wallet_balance": 0,
        "activation_wallet": 0,
        "matching_wallet": 0,
        "referral_code": referral_code,
        "sponsor_id": sponsor_user_id,
        "direct_referrals": [],
        "power_leg_user": None,
        "other_leg_users": [],
        "matched_pairs": 0,
        "total_income": 0,
        "commission_received": 0,
        "income_history": []
    }
    sponsor['direct_referrals'].append(user_id)
    leg_data = calculate_power_leg(sponsor_user_id, users_db)
    sponsor['power_leg_user'] = leg_data.get('power_leg_user')
    sponsor['other_leg_users'] = [d for d in sponsor['direct_referrals'] if d != leg_data.get('power_leg_user')]
    users_db[user_id] = user
    save_db(users_db)
    print(f"✅ Created INACTIVE user: {user['username']}")
    return user, None

@app.after_request
def set_response_headers(response):
    # Disable caching headers, WITHOUT 'ETag' or timestamp headers that cause refresh/login break
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, public, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Remaining routes and API endpoints exactly same as in your original code...

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if user_id and user:
        if user['is_admin']:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    session.clear()
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if user_id and user and not user.get('is_admin'):
        return redirect(url_for('user_dashboard'))
    session.clear()
    return render_template('signup.html')

@app.route('/dashboard')
def user_dashboard():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if not user_id or not user or user.get('is_admin'):
        session.clear()
        return redirect(url_for('login_page'))
    return render_template('user_panel.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if not user_id or not user or not user.get('is_admin'):
        session.clear()
        return redirect(url_for('login_page'))
    return render_template('admin_panel.html')

# API endpoints for auth, user, admin same as your code...

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    print(f"Server error: {e}")
    return jsonify({'error': 'Server error'}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    print(f"\n🚀 Server starting on port {port}")
    print(f"📝 Admin: admin / admin123")
    print(f"📂 Database: {DB_FILE}")
    print(f"📊 Users loaded: {len(users_db)}")
    print(f"👥 Max Directs per user: {MAX_DIRECTS}")
    print(f"💳 Activation Cost: ${ACTIVATION_COST}")
    print(f"💰 Matching Income: ${MATCHING_PER_PAIR} per pair")
    print(f"📈 Level Income: Levels 1-30\n")
    app.run(host='0.0.0.0', port=port, debug=False)
