from flask import Flask, redirect, url_for
from flask_cors import CORS
from models import db
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///juris.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'change_this_secret_to_a_secure_random_string')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', app.config['JWT_SECRET_KEY'])
    app.config['JWT_ALGORITHM'] = 'HS256'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 7200  
    
    CORS(app)
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        create_admin_user()
    
    from app.routes import user_bp, matter_bp, consult_bp, assignment_bp, proposal_bp
    from app.admin import init_admin
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(matter_bp, url_prefix='/api')
    app.register_blueprint(consult_bp, url_prefix='/api')
    app.register_blueprint(assignment_bp, url_prefix='/api')
    app.register_blueprint(proposal_bp, url_prefix='/api')
    init_admin(app)

    @app.get('/')
    def root():
        return redirect(url_for('admin_login_form'))

    @app.get('/api/health')
    def health_check():
        return {'status': 'ok'}, 200
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    return app


def create_admin_user():
    from models import User, UserRole
    
    admin = User.query.filter_by(email='admin@juris.com').first()
    if not admin:
        hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin = User(
            email='admin@juris.com',
            password=hashed_password,
            role=UserRole.ADMIN
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuario admin creado: admin@juris.com / admin123")
