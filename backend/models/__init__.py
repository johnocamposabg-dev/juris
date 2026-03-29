from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .models import User, Matter, Consult, ConsultAssignment, Proposal, UserRole, ConsultStatus, ProposalStatus