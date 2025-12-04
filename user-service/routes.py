from flask import Blueprint, request, jsonify, render_template, session, url_for, redirect
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import mongo
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies, jwt_required, get_jwt_identity, verify_jwt_in_request
from functools import wraps
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

def redirect_if_authenticated(f):
    """
    Decorator that redirects the user to the account page if a valid, non-expired JWT is found.
    Uses try/except to suppress errors from expired tokens, allowing the login/register page to render.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_id = None
        
        try:
            # 1. Attempt to verify the JWT. This will raise an exception if the token is expired/invalid.
            verify_jwt_in_request(optional=True) 
            
            # 2. If verification was successful (no exception), get the identity.
            current_user_id = get_jwt_identity()
            
        except (ExpiredSignatureError, InvalidTokenError) as e:
            # 3. Catch expired or invalid token errors. 
            # We silently ignore the error and leave current_user_id as None.
            print(f"Token expiration/invalidity handled in decorator: {e}")
            pass
            
        # --- Check for successful authentication ---
        if current_user_id is not None:
            # 4. If an identity exists, the user is already logged in. Redirect.
            return redirect(url_for("users.account_page"))
            
        # 5. If not authenticated, proceed to execute the original view function (render the page).
        return f(*args, **kwargs)
    return decorated_function

user_bp = Blueprint("users", __name__)

# POST /users
@user_bp.route("/api/users", methods=["POST"])
def create_user():
    data = request.json
    users = mongo.db.users

    email = data.get("email", "").strip().lower()

    # check if email has been registered
    existing = users.find_one({"email": email})
    if existing:
        return jsonify({"error": "Email already registered."}), 400
    
    new_user = {
        "name": data.get("name"),
        "email": email,
        "password": generate_password_hash(data.get("password"))
    }

    user_id = users.insert_one(new_user).inserted_id

    # Generate Token
    access_token = create_access_token(identity=str(user_id))

    # 2. set Token as HTTP-Only Cookie
    response = jsonify({"message": "Registered successfully"})
    set_access_cookies(response, access_token)

    return response, 200


# GET /users/<id>
@user_bp.route("/api/users/<id>", methods=["GET"])
def get_user(id):
    users = mongo.db.users
    user = users.find_one({"_id": ObjectId(id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"]
    }), 200


# POST /login
@user_bp.route("/api/login", methods=["POST"])
def login():
    data = request.json

    # Get user db collections
    users = mongo.db.users
    
    # Find the user by email
    user = users.find_one({"email": data.get("email")})

    if not user or not check_password_hash(user["password"], data.get("password")):
        return jsonify({"error": "Invalid login"}), 401

    # Generate Token
    access_token = create_access_token(identity=str(user["_id"]))

    # 2. set Token as HTTP-Only Cookie
    response = jsonify({"message": "Login succes"})
    set_access_cookies(response, access_token)
    return response, 200


@user_bp.route("/api/logout", methods=["POST"])
def logout():
    # 1. Create a response object
    response = jsonify({"message": "Logout successful"})
    # Clear the JWT cookie (tells the browser to delete the stored token)
    unset_jwt_cookies(response)
    # Return a JSON response for the frontend to handle redirection
    return response, 200

@user_bp.route("/api/me", methods=["GET"])
@jwt_required()
def get_current_user():
    
    # 1. === Extract User ID from JWT ===
    # The @jwt_required() decorator guarantees the request is authenticated.
    # get_jwt_identity() retrieves the user_id that was encoded into the token during login.
    current_user_id = get_jwt_identity()

    # 2. Get the user from db using the ID extracted from the token
    try:
        # Use the ID extracted from the JWT to query the database
        user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})
    except Exception as e:
        # Handle cases where the ID inside the token might be malformed (e.g., not a valid ObjectId)
        print(f"Error converting ID from JWT: {e}")
        return jsonify({"error": "Invalid token format or identity"}), 401
    
    # 3. Check if user exists (user might have been deleted after token issuance)
    if not user:
        return jsonify({"error": "User associated with token not found"}), 404

    # 4. Return user details
    return jsonify({
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        # Use .get() for safety in case the field is missing
        "subscription": user.get("subscription") 
    }), 200

@user_bp.route('/')
def index():
    # Sample data for courses
    featured_courses = [
        {"title": "Python for Absolute Beginners", "desc": "Master Python fundamentals and start building projects today."},
        {"title": "Front-End Development: React", "desc": "Build modern, high-performance web applications using React."},
        {"title": "Data Analysis & Visualization", "desc": "Learn to use Pandas and Matplotlib for powerful data insights."},
    ]
    return render_template('index.html', courses=featured_courses)

@user_bp.route("/login")
@redirect_if_authenticated
def login_page():
    return render_template("login.html")

@user_bp.route("/register")
@redirect_if_authenticated
def register_page():
    return render_template("register.html")

@user_bp.route("/account")
def account_page():
    # 1. Attempt to verify the JWT. 
    # This step loads the user's identity if a valid token is present in the cookie.
    verify_jwt_in_request(optional=True) 

    # 2. Check if the identity was successfully loaded (i.e., user is logged in).
    # get_jwt_identity() returns None if no valid token was loaded in the previous step.
    current_user_id = get_jwt_identity()
    if current_user_id is None:
        # 3. If no identity is found, redirect to the login page.
        return redirect(url_for("users.login_page"))
        
    # 4. If identity is found, render the page.
    return render_template("account.html")
