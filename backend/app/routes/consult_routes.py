from flask import Blueprint, request, jsonify
from .user_routes import token_required, admin_required
from models import Consult, ConsultStatus, UserRole, db, ConsultAssignment, Proposal, ProposalStatus
from datetime import datetime, timedelta


def create_consult_bp():
    consult_bp = Blueprint('consults', __name__, url_prefix='/consults')

    @consult_bp.route('', methods=['POST'])
    @token_required
    def create_consult(current_user):
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        required = ['matter_id', 'title', 'description']
        for f in required:
            if not data.get(f):
                return jsonify({'error': f'{f} is required'}), 400

        consult = Consult(
            matter_id=data['matter_id'],
            client_id=current_user.id,
            title=data['title'],
            description=data['description'],
            urgent=bool(data.get('urgent', False)),
            status=ConsultStatus.PENDING
        )
        db.session.add(consult)
        db.session.commit()

        return jsonify({'message': 'Consult created successfully', 'consult_id': consult.id}), 201
    
    @consult_bp.route('/<int:consult_id>', methods=['GET'])
    @token_required
    def get_consult(current_user, consult_id):
        consult = Consult.query.get(consult_id)
        if not consult:
            return jsonify({'error': 'Consult not found'}), 404

        if current_user.role not in (UserRole.ADMIN, UserRole.LAWYER) and consult.client_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403

        return jsonify({
            'id': consult.id,
            'client_id': consult.client_id,
            'matter_id': consult.matter_id,
            'title': consult.title,
            'description': consult.description,
            'urgent': consult.urgent,
            'status': consult.status.value,
            'created_at': consult.created_at.isoformat(),
            'updated_at': consult.updated_at.isoformat()
        }), 200
    
    @consult_bp.route('/<int:consult_id>', methods=['PUT'])
    @token_required
    def update_consult(current_user, consult_id):
        consult = Consult.query.get(consult_id)
        if not consult:
            return jsonify({'error': 'Consult not found'}), 404

        if current_user.role not in (UserRole.ADMIN, UserRole.LAWYER) and consult.client_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403

        data = request.get_json() or {}
        if 'title' in data:
            consult.title = data['title']
        if 'description' in data:
            consult.description = data['description']
        if 'urgent' in data:
            consult.urgent = bool(data['urgent'])
        if 'status' in data:
            try:
                consult.status = ConsultStatus(data['status'])
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400

        db.session.commit()
        return jsonify({'message': 'Consult updated successfully'}), 200   
    
    @consult_bp.route('/<int:consult_id>', methods=['DELETE'])
    @token_required
    @admin_required
    def delete_consult(current_user, consult_id):
        consult = Consult.query.get(consult_id)
        if not consult:
            return jsonify({'error': 'Consult not found'}), 404

        db.session.delete(consult)
        db.session.commit()
        return jsonify({'message': 'Consult deleted successfully'}), 200

    @consult_bp.route('/matter/<int:matter_id>', methods=['GET'])
    @token_required
    def get_consults_by_matter(current_user, matter_id):
        if current_user.role == UserRole.LAWYER:
            # Lawyers see only public, non-expired consults
            consults = Consult.query.filter_by(matter_id=matter_id, is_public=True).filter(Consult.expires_at > datetime.utcnow()).all()
        else:
            # Clients and admins see their own or all
            consults = Consult.query.filter_by(matter_id=matter_id).all()
        return jsonify([{
            'id': consult.id,
            'client_id': consult.client_id,
            'matter_id': consult.matter_id,
            'title': consult.title,
            'description': consult.description,
            'urgent': consult.urgent,
            'is_public': consult.is_public,
            'status': consult.status.value,
            'expires_at': consult.expires_at.isoformat()
        } for consult in consults]), 200
    
    @consult_bp.route('/status/<string:status>', methods=['GET'])
    @token_required
    def get_consults_by_status(current_user, status):
        try:
            consult_status = ConsultStatus(status)
        except ValueError:
            return jsonify({'error': 'Invalid consult status'}), 400

        consults = Consult.query.filter_by(status=consult_status).all()
        return jsonify([{
            'id': consult.id,
            'client_id': consult.client_id,
            'matter_id': consult.matter_id,
            'title': consult.title,
            'description': consult.description,
            'urgent': consult.urgent,
            'status': consult.status.value
        } for consult in consults]), 200

    @consult_bp.route('/user/<int:user_id>', methods=['GET'])
    @token_required
    def get_consults_by_user(current_user, user_id):
        if current_user.role not in (UserRole.ADMIN, UserRole.LAWYER) and current_user.id != user_id:
            return jsonify({'error': 'Access denied'}), 403

        consults = Consult.query.filter_by(client_id=user_id).all()
        return jsonify([{
            'id': consult.id,
            'client_id': consult.client_id,
            'matter_id': consult.matter_id,
            'title': consult.title,
            'description': consult.description,
            'urgent': consult.urgent,
            'status': consult.status.value
        } for consult in consults]), 200

    @consult_bp.route('/<int:consult_id>/make-public', methods=['PUT'])
    @token_required
    def make_consult_public(current_user, consult_id):
        consult = Consult.query.get(consult_id)
        if not consult or consult.client_id != current_user.id:
            return jsonify({'error': 'Consult not found or access denied'}), 404

        # Reset to public, remove assignments, reset proposals
        consult.is_public = True
        consult.status = ConsultStatus.PENDING
        consult.expires_at = datetime.utcnow() + timedelta(days=15)

        # Delete assignments
        ConsultAssignment.query.filter_by(consult_id=consult_id).delete()
        # Reset proposals
        Proposal.query.filter_by(consult_id=consult_id).update({'status': ProposalStatus.PENDING})

        db.session.commit()
        return jsonify({'message': 'Consult made public again'}), 200

    @consult_bp.route('/cleanup-expired', methods=['DELETE'])
    @token_required
    @admin_required
    def cleanup_expired_consults(current_user):
        expired_consults = Consult.query.filter(Consult.expires_at < datetime.utcnow(), Consult.is_public == True).all()
        for consult in expired_consults:
            db.session.delete(consult)
        db.session.commit()
        return jsonify({'message': f'Deleted {len(expired_consults)} expired consults'}), 200

    return consult_bp
