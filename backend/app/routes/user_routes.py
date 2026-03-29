from flask import Blueprint, request, jsonify, current_app
import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps
from models import User, UserRole, db


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            token = token.split(" ")[1]  
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(payload['user_id'])
            if not current_user:
                return jsonify({"error": "User not found"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.role != UserRole.ADMIN:
            return jsonify({"error": "Admin access required"}), 403
        return f(current_user, *args, **kwargs)
    return decorated


def create_user_bp():
    user_bp = Blueprint('user', __name__, url_prefix='/users')

    @user_bp.route('', methods=['POST'])
    def create_user():
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 400

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(email=email, password=hashed_password, role=UserRole.CLIENT)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "message": "User created successfully",
            "user_id": new_user.id,
            "email": new_user.email,
            "role": new_user.role.value
        }), 201
    
    @user_bp.route('/<int:user_id>', methods=['GET'])
    def get_user_by_id(user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value
        }), 200
    
    @user_bp.route('/<int:user_id>', methods=['PUT'])
    @token_required
    def update_user(current_user, user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        email = data.get("email")
        password = data.get("password")

        if email:
            if User.query.filter_by(email=email).first():
                return jsonify({"error": "Email already exists"}), 400
            user.email = email
        
        if password:
            user.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        db.session.commit()

        return jsonify({
            "message": "User updated successfully",
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value
        }), 200
    
    @user_bp.route('/<int:user_id>', methods=['DELETE'])
    @token_required
    def delete_user(current_user, user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        db.session.delete(user)
        db.session.commit()

        return jsonify({"message": "User deleted successfully"}), 200
    
    @user_bp.route('/users', methods=['GET'])
    @token_required
    @admin_required
    def list_users():
        users = User.query.all()
        return jsonify([{
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value
        } for user in users]), 200
    
    @user_bp.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return jsonify({"error": "Invalid email or password"}), 401

        payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(hours=2)
        }
        token = jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

        return jsonify({
            "message": "Login successful",
            "access_token": token,
            "user": {
                "user_id": user.id,
                "email": user.email,
                "role": user.role.value
            }
        }), 200
    
    @user_bp.route('/<int:user_id>/change_password', methods=['POST'])
    def change_password( user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not old_password or not new_password:
            return jsonify({"error": "Old password and new password are required"}), 400

        if not bcrypt.checkpw(old_password.encode('utf-8'), user.password.encode('utf-8')):
            return jsonify({"error": "Old password is incorrect"}), 401

        user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.session.commit()

        return jsonify({"message": "Password changed successfully"}), 200
    
    @user_bp.route('/<int:user_id>/role', methods=['POST'])
    @token_required
    @admin_required
    def change_role(current_user, user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        new_role = data.get("role")
        if not new_role:
            return jsonify({"error": "New role is required"}), 400

        try:
            user.role = UserRole[new_role.upper()]
        except KeyError:
            return jsonify({"error": f"Invalid role. Valid roles are: {', '.join([r.name for r in UserRole])}"}), 400

        db.session.commit()

        return jsonify({
            "message": "User role updated successfully",
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value
        }), 200
    
    @user_bp.route('/search', methods=['GET'])
    def search_users():
        query = request.args.get('q', '')
        users = User.query.filter(User.email.ilike(f'%{query}%')).all()
        return jsonify([{
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value
        } for user in users]), 200
    
    @user_bp.route('/<int:user_id>/consults', methods=['GET'])
    def get_user_consults(user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        consults = user.consults
        return jsonify([{
            "consult_id": consult.id,
            "title": consult.title,
            "description": consult.description,
            "status": consult.status.value,
            "created_at": consult.created_at.isoformat(),
            "updated_at": consult.updated_at.isoformat()
        } for consult in consults]), 200
    
    @user_bp.route('/<int:user_id>/assignments', methods=['GET'])
    @token_required
    def get_user_assignments(current_user, user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        assignments = user.assignments
        return jsonify([{
            "assignment_id": assignment.id,
            "consult_id": assignment.consult_id,
            "lawyer_id": assignment.lawyer_id,
            "assigned_at": assignment.assigned_at.isoformat()
        } for assignment in assignments]), 200
    
    @user_bp.route('/<int:user_id>/consults/count', methods=['GET'])
    def count_user_consults(user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        consult_count = len(user.consults)
        return jsonify({"consult_count": consult_count}), 200
    
    @user_bp.route('/create/staff', methods=['POST'])
    @token_required
    @admin_required
    def create_staff():
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 400

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(email=email, password=hashed_password, role=UserRole.STAFF)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "message": "Staff user created successfully",
            "user_id": new_user.id,
            "email": new_user.email,
            "role": new_user.role.value
        }), 201

    return user_bp

