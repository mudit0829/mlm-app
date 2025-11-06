from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import uuid
import os

app = Flask(__name__, template_folder='templates')
CORS(app)

users = {}

admin_user = {
    "user_id": "admin-1",
    "username": "admin",
    "password": "admin123",
    "sponsor_id": None,
    "directs": [],
    "power_leg": None,
    "other_leg": [],
    "is_admin": True,
    "email": "admin@tradeera.com",
    "first_name": "Admin",
    "last_name": "User",
    "dob": "",
    "country": "India",
    "mobile": "",
    "state": "",
    "position": "",
    "reg_date": ""
}
users[admin_user["user_id"]] = admin_user

def create_user(data):
    user_id = str(uuid.uuid4())
    user = {
        "user_id": user_id,
        "username": data['username'],
        "password": data['password'],
        "sponsor_id": data.get('referral_code'),
        "directs": [],
        "power_leg": None,
        "other_leg": [],
        "is_admin": False,
        "email": data['email'],
        "first_name": data['first_name'],
        "last_name": data['last_name'],
        "dob": data.get('dob', ''),
        "country": data.get('country', ''),
        "mobile": data.get('mobile', ''),
        "state": data.get('state', ''),
        "position": data.get('position', ''),
        "country_code": data.get('country_code', ''),
        "reg_date": data.get("reg_date", "")
    }
    users[user_id] = user
    
    # Placement logic
    sponsor_id = data.get('referral_code')
    if sponsor_id and sponsor_id in users:
        sponsor = users[sponsor_id]
        if data.get('position') == "LEFT":
            left_count = sum(1 for uid in sponsor['directs'] if users[uid].get('position') == 'LEFT')
            if left_count >= 6:
                return None, "Left position filled under this sponsor"
            sponsor['directs'].append(user_id)
            if not sponsor['power_leg'] or sponsor['power_leg'] == user_id:
                sponsor['power_leg'] = user_id
        else:
            right_count = sum(1 for uid in sponsor['directs'] if users[uid].get('position') == 'RIGHT')
            if right_count >= 6:
                return None, "Right position filled under this sponsor"
            sponsor['directs'].append(user_id)
            sponsor['other_leg'].append(user_id)
    
    return user, None

# SERVE HTML PAGES
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin-dashboard', methods=['GET'])
def admin_dashboard():
    return render_template('admin_dashboard.html')

# API ENDPOINTS
@app.route('/api/signup', methods=['POST'])
def api_signup():
    """Handle user signup"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['username', 'password', 'email', 'first_name', 'last_name', 'dob', 'country', 'mobile', 'state', 'position']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing)}'
            }), 400
        
        # Check for unique username
        if any(u['username'].lower() == data['username'].lower() for u in users.values()):
            return jsonify({
                'success': False,
                'message': 'Username already exists'
            }), 400
        
        # Check for unique email
        if any(u['email'].lower() == data['email'].lower() for u in users.values()):
            return jsonify({
                'success': False,
                'message': 'Email already registered'
            }), 400
        
        # Create user
        user, error = create_user(data)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user_id': user['user_id'],
            'username': user['username']
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle user login"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password required'
            }), 400
        
        # Find user
        for uid, user in users.items():
            if user['username'].lower() == username.lower() and user['password'] == password:
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'user_id': uid,
                    'username': user['username'],
                    'is_admin': user['is_admin'],
                    'email': user['email'],
                    'name': f"{user['first_name']} {user['last_name']}"
                }), 200
        
        return jsonify({
            'success': False,
            'message': 'Invalid username or password'
        }), 401
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/check-username/<username>', methods=['GET'])
def check_username(username):
    """Check if username exists"""
    try:
        exists = any(u['username'].lower() == username.lower() for u in users.values())
        if exists:
            return jsonify({'exists': True}), 200
        return jsonify({'exists': False}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users/by-username/<username>', methods=['GET'])
def get_user_by_username(username):
    """Get user by username (for backward compatibility)"""
    try:
        for user in users.values():
            if user['username'].lower() == username.lower():
                return jsonify(user), 200
        return jsonify({'message': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Handle admin login"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password required'
            }), 400
        
        # Find admin user
        for uid, user in users.items():
            if user['username'].lower() == username.lower() and user['password'] == password and user['is_admin']:
                return jsonify({
                    'success': True,
                    'message': 'Admin login successful',
                    'user_id': uid,
                    'username': user['username'],
                    'is_admin': True
                }), 200
        
        return jsonify({
            'success': False,
            'message': 'Invalid admin credentials'
        }), 401
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/<admin_id>/users', methods=['GET'])
def get_all_users(admin_id):
    """Get all users (admin only)"""
    try:
        user = users.get(admin_id)
        if not user or not user['is_admin']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        return jsonify({
            'success': True,
            'users': list(users.values())
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user details"""
    try:
        user = users.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        return jsonify({
            'success': True,
            'user': user
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
