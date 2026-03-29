from flask import Blueprint, request, jsonify
from .user_routes import token_required
from models import Proposal, ProposalStatus, UserRole, db, Consult
from datetime import datetime


def create_proposal_bp():
    proposal_bp = Blueprint('proposals', __name__, url_prefix='/proposals')

    @proposal_bp.route('', methods=['POST'])
    @token_required
    def create_proposal(current_user):
        if current_user.role != UserRole.LAWYER:
            return jsonify({'error': 'Only lawyers can send proposals'}), 403

        data = request.get_json()
        if not data or not data.get('consult_id') or not data.get('message'):
            return jsonify({'error': 'consult_id and message are required'}), 400

        consult = Consult.query.get(data['consult_id'])
        if not consult or not consult.is_public or consult.expires_at < datetime.utcnow():
            return jsonify({'error': 'Consult not available for proposals'}), 400

        # Check if lawyer already sent a proposal
        existing = Proposal.query.filter_by(consult_id=data['consult_id'], lawyer_id=current_user.id).first()
        if existing:
            return jsonify({'error': 'You already sent a proposal for this consult'}), 400

        new_proposal = Proposal(
            consult_id=data['consult_id'],
            lawyer_id=current_user.id,
            message=data['message']
        )
        db.session.add(new_proposal)
        db.session.commit()
        return jsonify({'message': 'Proposal sent successfully', 'proposal_id': new_proposal.id}), 201

    @proposal_bp.route('/consult/<int:consult_id>', methods=['GET'])
    @token_required
    def get_proposals_by_consult(current_user, consult_id):
        consult = Consult.query.get(consult_id)
        if not consult or consult.client_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403

        proposals = Proposal.query.filter_by(consult_id=consult_id).all()
        return jsonify([{
            'id': proposal.id,
            'lawyer_id': proposal.lawyer_id,
            'message': proposal.message,
            'status': proposal.status.value,
            'created_at': proposal.created_at.isoformat()
        } for proposal in proposals]), 200

    @proposal_bp.route('/<int:proposal_id>/accept', methods=['PUT'])
    @token_required
    def accept_proposal(current_user, proposal_id):
        proposal = Proposal.query.get(proposal_id)
        if not proposal:
            return jsonify({'error': 'Proposal not found'}), 404

        consult = proposal.consult
        if consult.client_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403

        # Accept this proposal, reject others
        proposal.status = ProposalStatus.ACCEPTED
        for p in consult.proposals:
            if p.id != proposal_id:
                p.status = ProposalStatus.REJECTED

        # Assign the consult to the lawyer
        from models import ConsultAssignment
        assignment = ConsultAssignment(consult_id=consult.id, lawyer_id=proposal.lawyer_id)
        db.session.add(assignment)

        # Make consult private
        consult.is_public = False
        consult.status = 'assigned'

        db.session.commit()
        return jsonify({'message': 'Proposal accepted and consult assigned'}), 200

    @proposal_bp.route('/<int:proposal_id>/reject', methods=['PUT'])
    @token_required
    def reject_proposal(current_user, proposal_id):
        proposal = Proposal.query.get(proposal_id)
        if not proposal:
            return jsonify({'error': 'Proposal not found'}), 404

        consult = proposal.consult
        if consult.client_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403

        proposal.status = ProposalStatus.REJECTED
        db.session.commit()
        return jsonify({'message': 'Proposal rejected'}), 200

    return proposal_bp