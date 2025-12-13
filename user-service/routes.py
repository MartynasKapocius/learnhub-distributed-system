import os
from dotenv import load_dotenv
import requests
from flask import Blueprint, request, jsonify, render_template, url_for, redirect, g
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import mongo
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies, jwt_required, get_jwt_identity, verify_jwt_in_request
from functools import wraps
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from utils.db import get_db, get_users_col

# load variable in .env
load_dotenv()

COURSE_SERVICE_URL = os.getenv(
    "COURSE_SERVICE_URL",
    "http://localhost:5001/courses"  # fallback
)

QUIZ_SERVICE_URL = os.getenv(
    "QUIZ_SERVICE_URL",
    "http://localhost:5002/quiz"  # fallback
)

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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.current_user is None:
            return redirect(url_for("users.login_page"))
        return f(*args, **kwargs)
    return decorated_function

user_bp = Blueprint("users", __name__)

# ========================================
# API Routes
# ========================================

# POST /users
@user_bp.route("/api/users", methods=["POST"])
def create_user():
    data = request.json
    
    # Get database and users collection
    db = get_db()
    users = db.users

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
@user_bp.route("/api/users/<id>", methods=["POST"])
def get_user(id):
    db = get_db()
    users = db.users
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
    db = get_db()
    users = db.users
    
    # Find the user by email
    user = users.find_one({"email": data.get("email")})

    if not user or not check_password_hash(user["password"], data.get("password")):
        return jsonify({"error": "Invalid login"}), 401

    # Generate Token
    access_token = create_access_token(identity=str(user["_id"]))

    # 2. set Token as HTTP-Only Cookie
    response = jsonify({"message": "Login success"})
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
        db = get_db()
        user = db.users.find_one({"_id": ObjectId(current_user_id)})
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
        "subscriptions": user.get("subscriptions", [])
    }), 200

@user_bp.route("/api/check-login")
def check_login():
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        return jsonify({"logged_in": user_id is not None})
    except:
        return jsonify({"logged_in": False})


@user_bp.route("/api/subscribe/<course_id>", methods=["POST"])
@jwt_required()
def subscribe_course(course_id):

    print("🔶 identity inside API:", get_jwt_identity())
    user_id = get_jwt_identity()
    users_col = get_users_col()

    print(users_col)

    # avoid duplicated subscription
    exists = users_col.find_one({
        "_id": ObjectId(user_id),
        "subscriptions.course_id": course_id
    })

    if exists:
        return jsonify({"error": "Already subscribed"}), 400

    users_col.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$push": {
                "subscriptions": {
                    "course_id": course_id,
                    "subscribed_at": datetime.utcnow(),
                    "status": "active"
                }
            }
        }
    )

    return jsonify({"success": True, "course_id": course_id})

@user_bp.route("/api/unsubscribe/<course_id>", methods=["DELETE"])
@jwt_required()
def unsubscribe_course(course_id):

    user_id = get_jwt_identity()
    users_col = get_users_col()

    # Remove subscription entry where course_id matches
    result = users_col.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"subscriptions": {"course_id": course_id}}}
    )

    if result.modified_count == 0:
        return jsonify({"error": "Subscription not found"}), 404

    return jsonify({"success": True, "course_id": course_id}), 200


@user_bp.route("/api/courses-data")
def courses_data():
    try:
        res = requests.get(f"{COURSE_SERVICE_URL}")
        res.raise_for_status()
        return jsonify(res.json())
    except:
        return jsonify([]), 200
    
@user_bp.route("/api/quiz/<course_id>", methods=["GET"])
@jwt_required()
def proxy_get_quiz(course_id):
    try:
        token = request.cookies.get("access_token_cookie")

        headers = {
            "Cookie": f"access_token_cookie={token}"
        }

        # for local run
        url = f"{QUIZ_SERVICE_URL}/{course_id}"

        res = requests.get(url, headers=headers)

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("Quiz proxy error:", e)
        return jsonify({"error": "Quiz service unavailable"}), 500
    
@user_bp.route("/api/submit", methods=["POST"])
def submit_quiz():
    data = request.json
    try:
        token = request.cookies.get("access_token_cookie")

        headers = {
            "Cookie": f"access_token_cookie={token}",
            "Content-Type": "application/json"
        }

        # for local run
        url = f"{QUIZ_SERVICE_URL}/submit"

        res = requests.post(url, headers=headers, json=data)

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("Quiz proxy error:", e)
        return jsonify({"error": "Quiz service unavailable"}), 500


# ========================================
# Page Routes
# ========================================

@user_bp.route('/')
def index():
    try:
        res = requests.get(f"{COURSE_SERVICE_URL}")
        courses = res.json()
        return render_template('index.html', courses=courses)
    except Exception as e:
        return jsonify({"error": f"Failed to reach course service: {str(e)}"}), 500

@user_bp.route("/courses/<course_id>")
def courses(course_id):
    try:
        # get Course Service one course
        res = requests.get(f"{COURSE_SERVICE_URL}/{course_id}")
        res.raise_for_status()

        course = res.json()

        return render_template("courses.html", course=course)

    except Exception as e:
        print("Error:", e)
        return render_template("error.html", message="Course not found"), 404
    
@user_bp.route("/quiz/<course_id>")
@login_required
def quiz_page(course_id):
    current_user = g.current_user
    
    subscriptions = current_user.get("subscriptions", [])

    is_subscribed = any(
        sub.get("course_id") == course_id and sub.get("status") == "active"
        for sub in subscriptions
    )

    if not is_subscribed:
        return redirect(url_for("home"))

    return render_template("quiz.html", course_id=course_id, user_id=current_user["_id"])


@user_bp.route("/subscriptions")
def subscriptions():
    
    # get all Courses Service
    res = requests.get(f"{COURSE_SERVICE_URL}")
    courses = res.json()  # list of courses

    return render_template("subscriptions.html", courses=courses)


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

@user_bp.before_app_request
def load_current_user():
    g.current_user = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()

        if user_id:
            users = get_users_col()
            user = users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
                g.current_user = user
    except:
        pass

@user_bp.app_context_processor
def inject_user_context():
    return {"current_user": getattr(g, "current_user", None)}