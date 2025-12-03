from flask import Blueprint, request, jsonify, render_template, session, url_for, redirect
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import mongo

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
    return jsonify({"id": str(user_id)}), 201


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

    session["user_id"] = str(user["_id"])

    return jsonify({"message": "Login success"}), 200

@user_bp.route("/api/me", methods=["GET"])
def get_current_user():
    # check if authenticated
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    # Get the user from db
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "subscription": user.get("subscription")
    })

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
def login_page():
    return render_template("login.html")

@user_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("users.login_page"))

@user_bp.route("/register")
def register_page():
    return render_template("register.html")

@user_bp.route("/account")
def account_page():
    if "user_id" not in session:
        return redirect(url_for("users.login_page"))
    return render_template("account.html")
