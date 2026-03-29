from flask import Blueprint, request, jsonify
from models import Matter, db
from .user_routes import token_required, admin_required
import jwt
from functools import wraps
from flask import current_app

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            token = token.split(" ")[1]  
            payload = jwt.decode(token, current_app.config.get('JWT_SECRET_KEY', 'change_this_secret'), algorithms=['HS256'])
            current_user = Matter.query.get(payload['user_id'])
            if not current_user:
                return jsonify({"error": "User not found"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated


def create_matter_bp():
    matter_bp = Blueprint('matters', __name__, url_prefix='/matters')

    @matter_bp.route('', methods=['POST'])
    @token_required
    @admin_required
    def create_matter(current_user):
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Name is required'}), 400

        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'Name cannot be empty'}), 400

        if Matter.query.filter_by(name=name).first():
            return jsonify({'error': 'Matter with this name already exists'}), 400

        new_matter = Matter(name=name)
        db.session.add(new_matter)
        db.session.commit()
        return jsonify({
            'message': 'Matter created successfully',
            'matter_id': new_matter.id,
            'name': new_matter.name
        }), 201

    @matter_bp.route('', methods=['GET'])
    def list_matters():
        matters = Matter.query.order_by(Matter.name).all()
        return jsonify([{'id': m.id, 'name': m.name} for m in matters]), 200

    @matter_bp.route('/<int:matter_id>', methods=['GET'])
    def get_matter(matter_id):
        matter = Matter.query.get(matter_id)
        if not matter:
            return jsonify({'error': 'Matter not found'}), 404
        return jsonify({'id': matter.id, 'name': matter.name}), 200

    @matter_bp.route('/<int:matter_id>', methods=['PUT'])
    @token_required
    @admin_required
    def update_matter(current_user, matter_id):
        matter = Matter.query.get(matter_id)
        if not matter:
            return jsonify({'error': 'Matter not found'}), 404

        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Name is required'}), 400

        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'Name cannot be empty'}), 400

        existing = Matter.query.filter(Matter.name==name, Matter.id != matter.id).first()
        if existing:
            return jsonify({'error': 'Matter with this name already exists'}), 400

        matter.name = name
        db.session.commit()
        return jsonify({'message': 'Matter updated successfully', 'id': matter.id, 'name': matter.name}), 200

    @matter_bp.route('/<int:matter_id>', methods=['DELETE'])
    @token_required
    @admin_required
    def delete_matter(current_user, matter_id):
        matter = Matter.query.get(matter_id)
        if not matter:
            return jsonify({'error': 'Matter not found'}), 404

        db.session.delete(matter)
        db.session.commit()
        return jsonify({'message': 'Matter deleted successfully'}), 200

    return matter_bp
