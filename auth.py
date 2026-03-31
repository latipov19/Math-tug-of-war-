import jwt
import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g
from models import UserModel
from config import Config

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


# ── JWT helpers ───────────────────────────────────────────────────────────────

def generate_token(user_id: int) -> str:
    payload = {
        'sub': user_id,
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        if not token:
            return jsonify({'error': 'Token required'}), 401
        try:
            data = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
            user = UserModel.get_by_id(data['sub'])
            if not user:
                return jsonify({'error': 'User not found'}), 401
            g.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.post('/register')
def register():
    data = request.get_json(silent=True) or {}
    username     = (data.get('username') or '').strip()
    email        = (data.get('email') or '').strip().lower()
    password     = data.get('password') or ''
    avatar_color = data.get('avatar_color', '#4fc3f7')

    # Validation
    if not username or len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if UserModel.exists_username(username):
        return jsonify({'error': 'Username already taken'}), 409
    if UserModel.exists_email(email):
        return jsonify({'error': 'Email already registered'}), 409

    user  = UserModel.create(username, email, password, avatar_color)
    token = generate_token(user['id'])
    return jsonify({'token': token, 'user': _public(user)}), 201


@auth_bp.post('/login')
def login():
    data     = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user = UserModel.get_by_username(username)
    if not user or not UserModel.verify_password(user, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    UserModel.update_last_login(user['id'])
    token = generate_token(user['id'])
    return jsonify({'token': token, 'user': _public(user)})


@auth_bp.get('/me')
@token_required
def me():
    return jsonify({'user': _public(g.current_user)})


def _public(user: dict) -> dict:
    return {k: v for k, v in user.items()
            if k not in ('password_hash',)}
