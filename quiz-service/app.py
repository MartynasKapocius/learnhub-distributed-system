import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'default-dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///quiz_service.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['COURSE_SERVICE_URL'] = os.environ.get('COURSE_SERVICE_URL', 'http://course-service:5001')
    app.config['RABBITMQ_URL'] = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')

    # JWT Configuration
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_SECURE'] = False
    app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
    app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token_cookie'

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    from routes import quiz_bp
    app.register_blueprint(quiz_bp)

    # Create tables
    with app.app_context():
        from models import Quiz, QuizSubmission
        try:
            db.create_all()
            logger.info("Database tables created successfully")
            # Verify database file exists
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                logger.info(f"Database file confirmed at: {db_path}")
            else:
                logger.warning(f"Database file not found at: {db_path}")
        except Exception as e:
            logger.error(f"Database creation failed: {e}")

    logger.info("Quiz Service started successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5002, debug=True)