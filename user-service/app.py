from flask import Flask, session
from extensions import mongo
from bson.objectid import ObjectId

def create_app():
    app = Flask(__name__)
    app.config["MONGO_URI"] = "mongodb://localhost:27017/users_db"

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
app.secret_key = "supersecret" 

@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    user = None
    if user_id:
        try:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        except:
            user = None
    return dict(current_user=user)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
