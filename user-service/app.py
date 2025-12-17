import os
from flask import Flask
from extensions import mongo, jwt
from dotenv import load_dotenv
from flask_cors import CORS

# load variable in .env
load_dotenv()

# Database name constant
DATABASE_NAME = "LearnHubDB"

def create_app():
    # --- 1. Environment Variable Retrieval and URI Construction ---
    
    # Read sensitive connection details from environment variables
    USERNAME = os.environ.get("MONGO_USERNAME")
    PASSWORD = os.environ.get("MONGO_PASSWORD")
    HOST = os.environ.get("MONGO_HOST")

    # Check for required variables
    if not all([USERNAME, PASSWORD, HOST]):
        # Raise an informative error if credentials are missing
        raise ValueError("Missing required MongoDB environment variables (USERNAME, PASSWORD, HOST)! Please check your .env file.")

    # Construct the MongoDB Atlas connection string (SRV format)
    MONGO_URI = f"mongodb+srv://{USERNAME}:{PASSWORD}@{HOST}/?appName=ds&tlsAllowInvalidCertificates=true"
    # -----------------------------------------------------------------

    # Create the Flask app instance
    app = Flask(__name__)

    CORS(app, supports_credentials=True)
    
    # Set app configuration (read from env variables)
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "default-dev-secret")
    
    # Set the MONGO_URI configuration key for Flask-PyMongo
    app.config["MONGO_URI"] = MONGO_URI

    app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
    app.config["JWT_REFRESH_COOKIE_PATH"] = "/"

    # 1. Setting: MUST be set to False for local development (http://localhost).
    # This tells Flask-JWT-Extended to allow cookies to be sent over non-HTTPS.
    app.config["JWT_COOKIE_SECURE"] = True 
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True

    # 2. Setting: Define SameSite policy for modern browsers
    # 'Lax' allows cookies to be sent on top-level navigation, which is necessary
    # if your frontend and backend are on different ports (e.g., 3000 vs 5000).
    app.config["JWT_COOKIE_SAMESITE"] = "None"

    # 3. Setting: Ensure the JWT extension knows to look for the token in cookies
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]

    # Optional: Setting a specific cookie name for clarity
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"
    
    # -----------------------------------------------------------------

    # Initialize extensions with the app instance
    jwt.init_app(app)
    mongo.init_app(app)

    # -----------------------
    # NOTE: Avoid accessing mongo.db here, as the application context 
    # might not be fully established, which can lead to connection issues.
    # Data operations should be done within request or application context.
    # -----------------------

    # Register Blueprints
    from routes import user_bp
    app.register_blueprint(user_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
