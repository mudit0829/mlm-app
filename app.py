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
    """Load users from JSON file"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(db):
    """Save users to JSON file"""
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
    """Count total team members (used for power leg calculation)"""
    count = 1
    user = db.get(user_id)
    if not user:
        return 0
    
    for direct_id in user.get('direct_referrals', []):
        count += count_team(direct_id, db)
    
    return count

def calculate_power_leg(user_id, db):
    """Calculate power leg and other leg counts"""
    user = db.get(user_id)
    if not user:
        return {'power_leg': 0, 'other_leg': 0}
    
    directs = user.get('direct_referrals', [])
    
    if len(directs) == 0:
        return {'power_leg': 0, 'other_leg': 0}
    
    power_leg_user_id = directs[0]
    power_leg_count = count_team(power_leg_user_id, db)
    
    other_leg_count = 0
    for i in range(1, len(directs)):
        other_leg_count += count_team(directs[i], db)
    
    return {
        'power_leg': power_leg_count,
        'other_leg': other_leg_count,
        'power_leg_user': power_leg_user_id
    }

def distribute_activation_income(user_id, db):
    """When user activates, distribute level income to upline sponsors"""
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
            
            print(f"💰 {sponsor['username']} earned ${income} from Level {level}")
        
        current_sponsor_id = sponsor.get('sponsor_id')
        level += 1

def calculate_matching_income(user_id, db):
    """Calculate and distribute matching income"""
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
        
        print(f"💰 {user['username']} earned ${income} from {pairs_increment} matching pairs")

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

# ===== FIX: DISABLE CACHING FOR ALL RESPONSES =====
@app.after_request
def set_response_headers(response):
    # Disable caching for all responses
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, public, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    # Remove these headers that cause auto-refresh and login issues:
    # response.headers['ETag'] = None
    # response.headers['X-Response-Time'] = str(datetime.now().timestamp())

    return response
# Routes
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

# AUTH API ENDPOINTS
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json() or {}
        username = data.get('username', '').lower()
        password = data.get('password', '')

        for uid, user in users_db.items():
            if user['username'].lower() == username and user['password'] == password:
                if user['status'] == 'inactive':
                    return jsonify({'success': False, 'message': 'Account inactive'}), 403
                session['user_id'] = uid
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                print(f"✅ Login: {username}")
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'user_id': uid,
                    'username': user['username'],
                    'is_admin': user['is_admin'],
                    'name': f"{user['first_name']} {user['last_name']}"
                }), 200

        print(f"❌ Login failed: {username}")
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    try:
        data = request.get_json() or {}

        required = ['username', 'password', 'email', 'first_name', 'last_name', 'dob', 'country', 'mobile', 'state', 'referral_code']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({'success': False, 'message': f'Missing: {", ".join(missing)}'}), 400

        user, error = create_user(data)
        if error:
            return jsonify({'success': False, 'message': error}), 400

        return jsonify({
            'success': True,
            'message': f'Registration successful! Account INACTIVE. Pay ${ACTIVATION_COST} to activate.',
            'user_id': user['user_id'],
            'referral_code': user['referral_code'],
            'activation_required': True,
            'activation_cost': ACTIVATION_COST
        }), 201

    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'}), 200

@app.route('/api/check-username/<username>', methods=['GET'])
def check_username(username):
    exists = any(u['username'].lower() == username.lower() for u in users_db.values())
    return jsonify({'exists': exists}), 200

# USER API ENDPOINTS
@app.route('/api/user/profile', methods=['GET'])
def get_profile():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if not user_id or not user or user.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    leg_data = calculate_power_leg(user_id, users_db)
    direct_count = len(user.get('direct_referrals', []))
    
    return jsonify({
        'success': True,
        'user': {
            'user_id': user['user_id'],
            'username': user['username'],
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'phone': user.get('mobile', ''),
            'country': user.get('country', ''),
            'state': user.get('state', ''),
            'dob': user.get('dob', ''),
            'wallet_balance': user.get('wallet_balance', 0),
            'activation_wallet': user.get('activation_wallet', 0),
            'matching_wallet': user.get('matching_wallet', 0),
            'referral_code': user['referral_code'],
            'total_income': user.get('total_income', 0),
            'total_directs': direct_count,
            'directs_remaining': MAX_DIRECTS - direct_count,
            'power_leg_count': leg_data['power_leg'],
            'other_leg_count': leg_data['other_leg'],
            'matched_pairs': user.get('matched_pairs', 0),
            'activation_status': user.get('activation_status'),
            'activation_cost': user.get('activation_cost'),
            'created_at': user.get('created_at')
        }
    }), 200

@app.route('/api/user/activate', methods=['POST'])
def activate_user():
    """User activates account with $100"""
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if not user_id or not user or user.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if user.get('activation_status') == 'active':
        return jsonify({'success': False, 'message': 'Already active'}), 400
    
    data = request.get_json() or {}
    payment_status = data.get('payment_status', 'success')
    
    if payment_status == 'success':
        user['activation_status'] = 'active'
        user['activation_date'] = datetime.now().isoformat()
        user['wallet_balance'] -= ACTIVATION_COST
        
        distribute_activation_income(user_id, users_db)
        
        current_sponsor_id = user.get('sponsor_id')
        while current_sponsor_id:
            calculate_matching_income(current_sponsor_id, users_db)
            sponsor = users_db.get(current_sponsor_id)
            if not sponsor:
                break
            current_sponsor_id = sponsor.get('sponsor_id')
        
        save_db(users_db)
        return jsonify({'success': True, 'message': f'Account activated! ${ACTIVATION_COST} deducted.'}), 200
    else:
        return jsonify({'success': False, 'message': 'Payment failed'}), 400

@app.route('/api/user/referrals', methods=['GET'])
def get_referrals():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if not user_id or not user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    referrals = []
    for i, ref_id in enumerate(user.get('direct_referrals', [])):
        ref_user = users_db.get(ref_id)
        if ref_user:
            is_power = (i == 0)
            referrals.append({
                'user_id': ref_user['user_id'],
                'username': ref_user['username'],
                'name': f"{ref_user['first_name']} {ref_user['last_name']}",
                'leg_type': 'Power Leg' if is_power else 'Other Leg',
                'activation_status': ref_user.get('activation_status'),
                'status': ref_user.get('status', ''),
                'joined': ref_user.get('created_at')
            })

    direct_count = len(user.get('direct_referrals', []))
    
    return jsonify({
        'success': True,
        'direct_count': direct_count,
        'max_directs': MAX_DIRECTS,
        'directs_remaining': MAX_DIRECTS - direct_count,
        'referrals': referrals
    }), 200

@app.route('/api/user/dashboard', methods=['GET'])
def get_dashboard():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if not user_id or not user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    leg_data = calculate_power_leg(user_id, users_db)
    direct_count = len(user.get('direct_referrals', []))
    
    return jsonify({
        'success': True,
        'dashboard': {
            'wallet_balance': user.get('wallet_balance', 0),
            'activation_wallet': user.get('activation_wallet', 0),
            'matching_wallet': user.get('matching_wallet', 0),
            'total_income': user.get('total_income', 0),
            'commission_received': user.get('commission_received', 0),
            'direct_referrals': direct_count,
            'directs_remaining': MAX_DIRECTS - direct_count,
            'max_directs': MAX_DIRECTS,
            'power_leg': leg_data['power_leg'],
            'other_leg': leg_data['other_leg'],
            'matched_pairs': user.get('matched_pairs', 0),
            'activation_status': user.get('activation_status'),
            'activation_cost': user.get('activation_cost'),
            'status': user.get('status', ''),
            'referral_code': user['referral_code'],
            'created_at': user.get('created_at')
        }
    }), 200

@app.route('/api/user/tree', methods=['GET'])
def get_tree_view():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
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
            "referral_code": u['referral_code'],
            "created_at": u.get('created_at'),
            "directs": []
        }
        for direct_id in u.get('direct_referrals', []):
            subtree = get_subtree(direct_id)
            if subtree:
                tree["directs"].append(subtree)
        return tree

    tree = get_subtree(user_id)
    return jsonify({'success': True, 'tree': tree}), 200

@app.route('/api/user/income-history', methods=['GET'])
def get_income_history():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if not user_id or not user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    return jsonify({
        'success': True,
        'income_history': user.get('income_history', [])
    }), 200

# ADMIN API ENDPOINTS
@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    user_id = session.get('user_id')
    user = users_db.get(user_id)
    if not user_id or not user or not user.get('is_admin'):
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    all_users = [
        {
            'user_id': u['user_id'],
            'username': u['username'],
            'email': u['email'],
            'name': f"{u['first_name']} {u['last_name']}",
            'phone': u.get('mobile', ''),
            'status': u.get('status', ''),
            'activation_status': u.get('activation_status'),
            'activation_wallet': u.get('activation_wallet', 0),
            'matching_wallet': u.get('matching_wallet', 0),
            'total_income': u.get('total_income', 0),
            'created_at': u.get('created_at'),
            'wallet_balance': u.get('wallet_balance', 0),
            'directs': len(u.get('direct_referrals', [])),
            'max_directs': MAX_DIRECTS
        }
        for u in users_db.values()
        if not u.get('is_admin')
    ]

    return jsonify({
        'success': True,
        'total_users': len(all_users),
        'users': all_users
    }), 200

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    user_id = session.get('user_id')
    admin = users_db.get(user_id)
    if not user_id or not admin or not admin.get('is_admin'):
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    total_users = len([u for u in users_db.values() if not u.get('is_admin')])
    active_users = len([u for u in users_db.values() if u.get('status') == 'active' and not u.get('is_admin')])
    pending_users = len([u for u in users_db.values() if u.get('status') == 'pending' and not u.get('is_admin')])
    activated_users = len([u for u in users_db.values() if u.get('activation_status') == 'active' and not u.get('is_admin')])
    inactive_users = total_users - activated_users
    total_activation_wallet = sum(u.get('activation_wallet', 0) for u in users_db.values() if not u.get('is_admin'))
    total_matching_wallet = sum(u.get('matching_wallet', 0) for u in users_db.values() if not u.get('is_admin'))

    return jsonify({
        'success': True,
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'pending_users': pending_users,
            'activated_users': activated_users,
            'inactive_users': inactive_users,
            'total_wallet_balance': sum(u.get('wallet_balance', 0) for u in users_db.values() if not u.get('is_admin')),
            'total_activation_wallet': total_activation_wallet,
            'total_matching_wallet': total_matching_wallet,
            'activation_cost': ACTIVATION_COST,
            'matching_per_pair': MATCHING_PER_PAIR
        }
    }), 200

@app.route('/api/admin/user/<user_id>/activate', methods=['PUT'])
def admin_activate_user(user_id):
    """Admin can activate user with custom cost ($100 or $0 for testing)"""
    user_id_admin = session.get('user_id')
    admin = users_db.get(user_id_admin)
    if not user_id_admin or not admin or not admin.get('is_admin'):
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    user = users_db.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    data = request.get_json() or {}
    action = data.get('action', 'activate')
    cost = float(data.get('cost', ACTIVATION_COST))
    
    if action == 'activate':
        user['activation_status'] = 'active'
        user['activation_date'] = datetime.now().isoformat()
        user['wallet_balance'] -= cost
        
        distribute_activation_income(user_id, users_db)
        
        current_sponsor_id = user.get('sponsor_id')
        while current_sponsor_id:
            calculate_matching_income(current_sponsor_id, users_db)
            sponsor = users_db.get(current_sponsor_id)
            if not sponsor:
                break
            current_sponsor_id = sponsor.get('sponsor_id')
        
        save_db(users_db)
        
        cost_text = f"${cost:.2f}" if cost > 0 else "FREE (Testing)"
        return jsonify({
            'success': True,
            'message': f'User activated with {cost_text} cost. Income distributed to upline.'
        }), 200
    else:
        user['activation_status'] = 'inactive'
        save_db(users_db)
        return jsonify({'success': True, 'message': 'User deactivated'}), 200

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
