from flask import Blueprint, request, jsonify
from .user_routes import token_required, admin_required
from models import ConsultAssignment, UserRole, db, Consult, ConsultStatus


def create_consult_assignment_bp():
    assignment_bp = Blueprint('assignments', __name__, url_prefix='/assignments')

    @assignment_bp.route('', methods=['POST'])
    @token_required
    def create_assignment(current_user):
        data = request.get_json()
        if not data or not data.get('consult_id') or not data.get('lawyer_id'):
            return jsonify({'error': 'consult_id and lawyer_id are required'}), 400

        consult = Consult.query.get(data['consult_id'])
        if not consult:
            return jsonify({'error': 'Consult not found'}), 404

        # Allow admin or client of the consult
        if current_user.role != UserRole.ADMIN and consult.client_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403

        new_assignment = ConsultAssignment(
            consult_id=data['consult_id'],
            lawyer_id=data['lawyer_id']
        )
        db.session.add(new_assignment)

        # Make consult private and assigned
        consult.is_public = False
        consult.status = ConsultStatus.ASSIGNED

        db.session.commit()
        return jsonify({'message': 'Consult assignment created successfully', 'assignment_id': new_assignment.id}), 201
    
    @assignment_bp.route('/<int:assignment_id>', methods=['GET'])
    @token_required
    def get_assignment(current_user, assignment_id):
        assignment = ConsultAssignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'error': 'Consult assignment not found'}), 404

        if current_user.role not in (UserRole.ADMIN, UserRole.LAWYER) and current_user.id != assignment.lawyer_id:
            return jsonify({'error': 'Access denied'}), 403

        return jsonify({
            'id': assignment.id,
            'consult_id': assignment.consult_id,
            'lawyer_id': assignment.lawyer_id,
            'assigned_at': assignment.assigned_at.isoformat(),
            'status': assignment.status
        }), 200
    
    @assignment_bp.route('/<int:assignment_id>', methods=['DELETE'])
    @token_required
    @admin_required
    def delete_assignment(current_user, assignment_id):
        assignment = ConsultAssignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'error': 'Consult assignment not found'}), 404
        
        db.session.delete(assignment)
        db.session.commit()
        return jsonify({'message': 'Consult assignment deleted successfully'}), 200
    
    @assignment_bp.route('/consult/<int:consult_id>', methods=['GET'])
    @token_required
    def get_assignments_by_consult(current_user, consult_id):
        assignments = ConsultAssignment.query.filter_by(consult_id=consult_id).all()
        return jsonify([{
            'id': assignment.id,
            'consult_id': assignment.consult_id,
            'lawyer_id': assignment.lawyer_id,
            'assigned_at': assignment.assigned_at.isoformat(),
            'status': assignment.status
        } for assignment in assignments]), 200

    @assignment_bp.route('/lawyer/<int:lawyer_id>', methods=['GET'])
    @token_required
    def get_assignments_by_lawyer(current_user, lawyer_id):
        if current_user.role not in (UserRole.ADMIN, UserRole.LAWYER) and current_user.id != lawyer_id:
            return jsonify({'error': 'Access denied'}), 403

        assignments = ConsultAssignment.query.filter_by(lawyer_id=lawyer_id).all()
        return jsonify([{
            'id': assignment.id,
            'consult_id': assignment.consult_id,
            'lawyer_id': assignment.lawyer_id,
            'assigned_at': assignment.assigned_at.isoformat(),
            'status': assignment.status
        } for assignment in assignments]), 200

    return assignment_bp
