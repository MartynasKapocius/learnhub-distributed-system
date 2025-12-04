import os
from flask import Flask, session
from extensions import mongo, jwt
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

# load variable in .env
load_dotenv()

def create_app():
    # create app
    app = Flask(__name__)
    
    # setting env variable
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "default-dev-secret")
    app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/learnhub_dev")

    # Initialize extensions with the app
    jwt.init_app(app)
    mongo.init_app(app)

    # ---- Debug ----
    # print(">>> mongo.db =", mongo.db)
    if mongo.db is not None:
      print(">>> collections =", mongo.db.list_collection_names())
    # -----------------------


    from routes import user_bp
    app.register_blueprint(user_bp)

    return app

app = create_app()

app.config["JWT_ACCESS_COOKIE_PATH"] = "/"

# 1. Setting: MUST be set to False for local development (http://localhost).
# This tells Flask-JWT-Extended to allow cookies to be sent over non-HTTPS.
app.config["JWT_COOKIE_SECURE"] = False 

# 2. Setting: Define SameSite policy for modern browsers
# 'Lax' allows cookies to be sent on top-level navigation, which is necessary
# if your frontend and backend are on different ports (e.g., 3000 vs 5000).
app.config["JWT_COOKIE_SAMESITE"] = "Lax" 

# 3. Setting: Ensure the JWT extension knows to look for the token in cookies
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]

# Optional: Setting a specific cookie name for clarity
app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"

@app.context_processor
def inject_user():
    """
    Context processor to make the current_user available in all Jinja2 templates,
    using try/except blocks to handle expired tokens gracefully.
    """
    
    current_user = None
    is_authenticated = False
    
    try:
        # 1. Attempt to verify the JWT. This will raise an exception if the token is expired or invalid.
        # optional=True is used here, so it only fails if a token is present but bad.
        is_verified = verify_jwt_in_request(optional=True)
        
        # Check if verification succeeded and an identity was loaded
        if is_verified:
            # If successful, get_jwt_identity() is safe to call
            current_user_id = get_jwt_identity()
            
            if current_user_id:
                # 2. Check complete, proceed to fetch user data
                user_id_obj = ObjectId(current_user_id)
                current_user = mongo.db.users.find_one({"_id": user_id_obj})
                is_authenticated = True
                
    except (ExpiredSignatureError, InvalidTokenError) as e:
        # 3. Catch JWT errors (expired or invalid signature)
        # We silently ignore the error and leave current_user as None.
        print(f"Token error handled in context processor: {e}")
        pass
    except Exception as e:
        # Catch errors from ObjectId conversion or DB access
        print(f"General error in context processor: {e}")
        pass
        
    # 4. Return the user object to the template context as 'current_user'
    return dict(current_user=current_user)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
