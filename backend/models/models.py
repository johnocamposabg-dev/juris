from flask_sqlalchemy import SQLAlchemy
from enum import Enum
from datetime import datetime, timedelta

# db is defined in __init__.py
from . import db


class UserRole(Enum):
    ADMIN = 'ADMIN'
    LAWYER = 'LAWYER'
    CLIENT = 'CLIENT'



class ConsultStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ProposalStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.CLIENT, nullable=False)


    consults = db.relationship("Consult", backref="client", lazy=True)
    assignments = db.relationship("ConsultAssignment", backref="lawyer", lazy=True)


class Matter(db.Model):
    __tablename__ = "matter"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


    consults = db.relationship("Consult", backref="matter", lazy=True)

    def __repr__(self):
        return f'<Matter {self.name}>'


class Consult(db.Model):
    __tablename__ = "consult"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    matter_id = db.Column(db.Integer, db.ForeignKey("matter.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    urgent = db.Column(db.Boolean, default=False, nullable=False)
    is_public = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=15), nullable=False)

    status = db.Column(
        db.Enum(ConsultStatus),
        default=ConsultStatus.PENDING,
        nullable=False
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


    assignments = db.relationship("ConsultAssignment", backref="consult", lazy=True)
    proposals = db.relationship("Proposal", backref="consult", lazy=True)

    def __repr__(self):
        return f'<Consult {self.title}>'


class ConsultAssignment(db.Model):
    __tablename__ = "consult_assignment"

    id = db.Column(db.Integer, primary_key=True)
    consult_id = db.Column(db.Integer, db.ForeignKey("consult.id"), nullable=False)
    lawyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)

    def __repr__(self):
        return f'<ConsultAssignment consult_id={self.consult_id}, lawyer_id={self.lawyer_id}>'


class Proposal(db.Model):
    __tablename__ = "proposal"

    id = db.Column(db.Integer, primary_key=True)
    consult_id = db.Column(db.Integer, db.ForeignKey("consult.id"), nullable=False)
    lawyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(ProposalStatus), default=ProposalStatus.PENDING, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f'<Proposal consult_id={self.consult_id}, lawyer_id={self.lawyer_id}>'