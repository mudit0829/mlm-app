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

# Database file (persistent storage)
DB_FILE = "users_db.json"

def load_db():
    """Load users from JSON file"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading DB: {e}")
    return {}

def save_db(db):
    """Save users to JSON file"""
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving DB: {e}")

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
    "created_at": datetime.now().isoformat(),
    "wallet_balance": 0,
    "referral_code": "ADMIN123",
    "sponsor_id": None,
    "position": "ADMIN",
    "directs": [],
    "power_leg": None,
    "other_leg": [],
    "total_income": 0,
    "phone": "",
    "country": "India",
    "state": "",
    "dob": ""
}

# Add admin if not in DB
if "admin-1" not in users_db:
    users_db["admin-1"] = ADMIN_USER
    save_db(users_db)

def generate_referral_code():
    return str(uuid.uuid4())[:8].upper()

def create_user(data):
    user_id = str(uuid.uuid4())
    referral_code = generate_referral_code()
    position = data.get('position')
    sponsor_code = data.get('referral_code')

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
        "position": position,
        "is_admin": False,
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "wallet_balance": 0,
        "referral_code": referral_code,
        "sponsor_id": sponsor_code,
        "directs": [],
        "power_leg": None,
        "other_leg": [],
        "total_income": 0,
        "commission_received": 0
    }

    # Find sponsor from referral code
    sponsor_user_id = None
    for uid, u in users_db.items():
        if u['referral_code'] == sponsor_code:
            sponsor_user_id = uid
            break
    if not sponsor_user_id:
        return None, "Invalid Referral Code"

    sponsor = users_db[sponsor_user_id]
    # Count directs on each side
    left_count = sum(1 for uid in sponsor['directs'] if users_db[uid]['position'] == 'LEFT')
    right_count = sum(1 for uid in sponsor['directs'] if users_db[uid]['position'] == 'RIGHT')

    if position == 'LEFT' and left_count >= 6:
        return None, "Left position already filled (6 max)"
    if position == 'RIGHT' and right_count >= 6:
        return None, "Right position already filled (6 max)"
    if position not in ['LEFT', 'RIGHT']:
        return None, "Invalid position"

    sponsor['directs'].append(user_id)
    if position == 'LEFT':
        if not sponsor['power_leg']:
            sponsor['power_leg'] = user_id
    else:
        sponsor['other_leg'].append(user_id)

    users_db[user_id] = user
    save_db(users_db)  # SAVE TO FILE
    return user, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    user_id = session.get('user_id')
    user = users_db.get(user_id) if user_id else None
    if user_id and user:
        if user['is_admin']:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    session.clear()
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    user_id = session.get('user_id')
    user = users_db.get(user_id) if user_id else None
    if user_id and user and not user.get('is_admin'):
        return redirect(url_for('user_dashboard'))
    session.clear()
    return render_template('signup.html')

@app.route('/dashboard')
def user_dashboard():
    user_id = session.get('user_id')
    user = users_db.get(user_id) if user_id else None
    if not user_id or not user or user['is_admin']:
        session.clear()
        return redirect(url_for('login_page'))
    return render_template('user_panel.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    user_id = session.get('user_id')
    user = users_db.get(user_id) if user_id else None
    if not user_id or not user or not user['is_admin']:
        session.clear()
        return redirect(url_for('login_page'))
    return render_template('admin_panel.html')

# AUTH API ENDPOINTS
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400

        for uid, user in users_db.items():
            if user['username'].lower() == username.lower() and user['password'] == password:
                if user['status'] == 'inactive':
                    return jsonify({'success': False, 'message': 'Account inactive'}), 403
                session['user_id'] = uid
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'user_id': uid,
                    'username': user['username'],
                    'is_admin': user['is_admin'],
                    'name': f"{user['first_name']} {user['last_name']}"
                }), 200
        session.clear()
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    except Exception as e:
        session.clear()
        print(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        required = ['username', 'password', 'email', 'first_name', 'last_name', 'dob', 'country', 'mobile', 'state', 'position', 'referral_code']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({'success': False, 'message': f'Missing: {", ".join(missing)}'}), 400

        if any(u['username'].lower() == data['username'].lower() for u in users_db.values()):
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        if any(u['email'].lower() == data['email'].lower() for u in users_db.values()):
            return jsonify({'success': False, 'message': 'Email already registered'}), 400

        user, error = create_user(data)
        if error:
            return jsonify({'success': False, 'message': error}), 400

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user_id': user['user_id'],
            'referral_code': user['referral_code']
        }), 201

    except Exception as e:
        print(f"Signup error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'}), 200

@app.route('/api/check-username/<username>', methods=['GET'])
def check_username(username):
    try:
        exists = any(u['username'].lower() == username.lower() for u in users_db.values())
        return jsonify({'exists': exists}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# USER API ENDPOINTS
@app.route('/api/user/profile', methods=['GET'])
def get_profile():
    user_id = session.get('user_id')
    user = users_db.get(user_id) if user_id else None
    if not user_id or not user or user.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    return jsonify({
        'success': True,
        'user': {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'phone': user['mobile'],
            'country': user['country'],
            'state': user['state'],
            'dob': user['dob'],
            'wallet_balance': user['wallet_balance'],
            'referral_code': user['referral_code'],
            'total_income': user['total_income'],
            'directs_count': len(user['directs']),
            'created_at': user.get('created_at')
        }
    }), 200

@app.route('/api/user/referrals', methods=['GET'])
def get_referrals():
    user_id = session.get('user_id')
    user = users_db.get(user_id) if user_id else None
    if not user_id or not user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    referrals = []
    for ref_id in user['directs']:
        ref_user = users_db.get(ref_id)
        if ref_user:
            referrals.append({
                'user_id': ref_user['user_id'],
                'username': ref_user['username'],
                'name': f"{ref_user['first_name']} {ref_user['last_name']}",
                'position': ref_user['position'],
                'status': ref_user['status'],
                'joined': ref_user['created_at']
            })

    return jsonify({
        'success': True,
        'direct_count': len(user['directs']),
        'referrals': referrals
    }), 200

@app.route('/api/user/dashboard', methods=['GET'])
def get_dashboard():
    user_id = session.get('user_id')
    user = users_db.get(user_id) if user_id else None
    if not user_id or not user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    return jsonify({
        'success': True,
        'dashboard': {
            'wallet_balance': user['wallet_balance'],
            'total_income': user['total_income'],
            'commission_received': user.get('commission_received', 0),
            'direct_referrals': len(user['directs']),
            'status': user['status'],
            'referral_code': user['referral_code'],
            'created_at': user.get('created_at')
        }
    }), 200

# TREE VIEW API - Binary Tree
@app.route('/api/user/tree', methods=['GET'])
def get_tree_view():
    user_id = session.get('user_id')
    user = users_db.get(user_id) if user_id else None
    if not user_id or not user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    def get_subtree(uid):
        u = users_db.get(uid)
        if not u:
            return None
        tree = {
            "user_id": u['user_id'],
            "username": u['username'],
            "name": f"{u['first_name']} {u['last_name']}",
            "position": u['position'],
            "referral_code": u['referral_code'],
            "created_at": u.get('created_at'),
            "left": None,
            "right": []
        }
        # Power_leg is LEFT, other_leg is RIGHT(s)
        if u.get("power_leg"):
            tree["left"] = get_subtree(u["power_leg"])
        if u.get("other_leg"):
            tree["right"] = [get_subtree(child_id) for child_id in u["other_leg"] if get_subtree(child_id)]
        return tree

    tree = get_subtree(user_id)
    return jsonify({'success': True, 'tree': tree}), 200

# ADMIN API ENDPOINTS
@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    user_id = session.get('user_id')
    user = users_db.get(user_id) if user_id else None
    if not user_id or not user or not user['is_admin']:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    all_users = []
    for uid, u in users_db.items():
        if not u['is_admin']:
            all_users.append({
                'user_id': u['user_id'],
                'username': u['username'],
                'email': u['email'],
                'name': f"{u['first_name']} {u['last_name']}",
                'phone': u['mobile'],
                'status': u['status'],
                'created_at': u['created_at'],
                'wallet_balance': u['wallet_balance'],
                'directs': len(u['directs'])
            })

    return jsonify({
        'success': True,
        'total_users': len(all_users),
        'users': all_users
    }), 200

@app.route('/api/admin/user/<user_id>/activate', methods=['PUT'])
def admin_activate_user(user_id):
    user_id_admin = session.get('user_id')
    admin = users_db.get(user_id_admin) if user_id_admin else None
    if not user_id_admin or not admin or not admin['is_admin']:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    user = users_db.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    data = request.get_json()
    user['status'] = data.get('status', 'active')
    save_db(users_db)  # SAVE TO FILE
    return jsonify({
        'success': True,
        'message': f'User {user_id} status changed to {user["status"]}'
    }), 200

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    user_id = session.get('user_id')
    admin = users_db.get(user_id) if user_id else None
    if not user_id or not admin or not admin['is_admin']:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    total_users = len([u for u in users_db.values() if not u['is_admin']])
    active_users = len([u for u in users_db.values() if u['status'] == 'active' and not u['is_admin']])
    pending_users = len([u for u in users_db.values() if u['status'] == 'pending' and not u['is_admin']])

    return jsonify({
        'success': True,
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'pending_users': pending_users,
            'total_wallet_balance': sum(u['wallet_balance'] for u in users_db.values() if not u['is_admin'])
        }
    }), 200

# ERROR HANDLERS
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    print(f"Server error: {str(e)}")
    return jsonify({'error': 'Server error'}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Server running on http://localhost:{port}")
    print(f"📝 Admin credentials: admin / admin123")
    print(f"📁 Database file: {DB_FILE}")
    app.run(host='0.0.0.0', port=port, debug=True)
