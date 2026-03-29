from flask import Blueprint
from .user_routes import create_user_bp
from .matter_routes import create_matter_bp
from .consult_routes import create_consult_bp
from .consult_assignment_routes import create_consult_assignment_bp
from .proposal_routes import create_proposal_bp

user_bp = create_user_bp()
matter_bp = create_matter_bp()
consult_bp = create_consult_bp()
assignment_bp = create_consult_assignment_bp()
proposal_bp = create_proposal_bp()
