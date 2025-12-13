import os
import logging
from flask import Flask
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import libsql_client
from flask_cors import CORS
# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_db_client():
    url = os.getenv("TURSO_URL")
    token = os.getenv("TURSO_TOKEN")

    if not url:
        raise RuntimeError("TURSO_URL is not set")
    
    # check Token 
    if not token:
        raise RuntimeError("TURSO_TOKEN is not set") 

    client = None
    try:
        # link to database
        client = libsql_client.create_client_sync(
            url=url,
            auth_token=token
        )
        
        logger.info("Connected to Turso (libSQL) successfully and verified.")
        return client
        
    except Exception as e:
        # catch error
        logger.error(f"Failed to connect or verify Turso (libSQL) connection: {e}")
        # return a clear error message to show the error.
        raise RuntimeError(f"Database initialization failed: {e}")



def create_app():
    app = Flask(__name__)
    
    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default-dev-secret')
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_SECURE"] = True  # allow local HTTP
    app.config["JWT_COOKIE_SAMESITE"] = "None"
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"

    # Initialize extensions
    jwt = JWTManager(app)

    # Attach Turso database client to app
    app.db = create_db_client()

    # Attach course service URL
    app.config["COURSE_SERVICE_URL"] = os.getenv(
        "COURSE_SERVICE_URL",
        "http://course-service:5001"
    )

    # RabbitMQ
    app.config["RABBITMQ_URL"] = os.getenv(
        "RABBITMQ_URL",
        "amqp://guest:guest@rabbitmq:5672/"
    )

    # Register blueprints
    from routes import quiz_bp
    app.register_blueprint(quiz_bp)

    logger.info("Quiz Service started successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    CORS(app, supports_credentials=True)
    app.run(host='0.0.0.0', port=5002, debug=True)