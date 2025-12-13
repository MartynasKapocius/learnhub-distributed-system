# Importing.
import os
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify, g
from pymongo import MongoClient
from bson import ObjectId
import pika
from mongo import get_mongo_client

# load variable in .env
load_dotenv()

def get_db():
    if "db" not in g:
        client = get_mongo_client()
        if client is None:
            g.db = None
        else:
            g.db = client[os.getenv("DATABASE_NAME", "LearnHubDB")]["courses"]
    return g.db

# Course Service.
def create_app():
    app = Flask(__name__)

    # Basic configuration.
    # === MongoDB Atlas Configuration ===
    # Read credentials from environment variables
    # MONGO_USERNAME = os.getenv("MONGO_USERNAME")
    # MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
    # MONGO_HOST = os.getenv("MONGO_HOST")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "LearnHubDB")  # Default to LearnHubDB

    # Construct MongoDB Atlas connection string (SRV format)
    # MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}/?appName=ds"

    # app.config["MONGO_URI"] = MONGO_URI
    app.config["DATABASE_NAME"] = DATABASE_NAME
    # =====================================

    # RabbitMQ configuration (optional)
    app.config["RABBITMQ_HOST"] = os.getenv("RABBITMQ_HOST", "rabbitmq")
    app.config["EVENT_EXCHANGE"] = os.getenv("EVENT_EXCHANGE", "learning_events")

    # MongoDB client and collection.
    # try:
    #     mongo_client = MongoClient(app.config["MONGO_URI"])
    #     # Explicitly specify the database
    #     db = mongo_client[DATABASE_NAME]
    #     course_col = db["courses"]
        
    #     # Test connection
    #     mongo_client.admin.command('ping')
    #     print(f"[Course Service] Connected to MongoDB Atlas: {MONGO_HOST}")
    #     print(f"[Course Service] Using database: {DATABASE_NAME}")
    # except Exception as e:
    #     print(f"[Course Service] Failed to connect to MongoDB: {e}")
    #     raise

    # Event publisher.
    def publish_event(event_type, payload):
        """
        Publishes a JSON event to RabbitMQ.
        If RabbitMQ is unreachable, log the error but do not break the API.
        """
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=app.config["RABBITMQ_HOST"])
            )
            channel = connection.channel()

            channel.exchange_declare(
                exchange=app.config["EVENT_EXCHANGE"],
                exchange_type="topic",
                durable=True
            )

            event = {"event_type": event_type, "payload": payload}

            channel.basic_publish(
                exchange=app.config["EVENT_EXCHANGE"],
                routing_key=f"course.{event_type}",
                body=json.dumps(event).encode("utf-8"),
            )

            connection.close()
            app.logger.info(f"Event published: {event_type}")

        except Exception as e:
            app.logger.error(f"Event publish failed: {e}")

    # Convert MongoDB document to a JSON safe dict.
    def to_json(doc):
        result = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                result["id"] = str(v)
            else:
                result[k] = v
        return result

    # Health check used by Docker/K8s.
    @app.get("/health")
    def health():
        db = get_db()
        if db is None:
            return jsonify({"error": "Database unavailable"}), 503
        try:
            count = db.estimated_document_count()
            return {"status": "ok", "db": "ok", "count": count}
        except Exception as e:
            app.logger.error(f"Health check DB error: {e}")
            return {"status": "error", "db": "unreachable"}, 500

    # Get all courses.
    @app.get("/courses")
    def get_courses():
        db = get_db()
        if db is None:
            return jsonify({"error": "Database unavailable"}), 503
        
        docs = list(db.find())
        return jsonify([to_json(d) for d in docs]), 200

    # Get a single course by ID.
    @app.get("/courses/<course_id>")
    def get_course(course_id):
        db = get_db()
        if db is None:
            return jsonify({"error": "Database unavailable"}), 503
        try:
            oid = ObjectId(course_id)
        except Exception:
            return {"error": "Invalid ID"}, 400
        
        doc = db.find_one({"_id": oid})
        if not doc:
            return {"error": "Course not found"}, 404

        return jsonify(to_json(doc)), 200

    # Create a new course.
    @app.post("/courses")
    def create_course():
        db = get_db()
        if db is None:
            return jsonify({"error": "Database unavailable"}), 503

        data = request.get_json() or {}
        title = data.get("title")
        description = data.get("description", "")

        if not title:
            return {"error": "title is required"}, 400

        result = db.insert_one({
            "title": title,
            "description": description
        })

        created = db.find_one({"_id": result.inserted_id})
        course_json = to_json(created)

        # This is where the service becomes event driven.
        publish_event("course_created", course_json)

        return jsonify(course_json), 201

    # Update an existing course.
    @app.put("/courses/<course_id>")
    def update_course(course_id):
        data = request.get_json() or {}
        db = get_db()
        if db is None:
            return jsonify({"error": "Database unavailable"}), 503
        # Validate ObjectId.
        try:
            oid = ObjectId(course_id)
        except Exception:
            return {"error": "Invalid ID"}, 400

        # Only update fields provided by the client.
        update_fields = {}
        if "title" in data:
            update_fields["title"] = data["title"]
        if "description" in data:
            update_fields["description"] = data["description"]

        # Nothing to update.
        if not update_fields:
            return {"error": "No fields to update"}, 400

        # Perform update in MongoDB.
        result = db.update_one({"_id": oid}, {"$set": update_fields})

        # Document does not exist.
        if result.matched_count == 0:
            return {"error": "Course not found"}, 404

        # Fetch updated record.
        updated = db.find_one({"_id": oid})
        updated_json = to_json(updated)

        # Notify other services.
        publish_event("course_updated", updated_json)

        return jsonify(updated_json), 200

    # Delete an existing course.
    @app.delete("/courses/<course_id>")
    def delete_course(course_id):
        # Validate ObjectId.
        db = get_db()
        if db is None:
            return jsonify({"error": "Database unavailable"}), 503
        
        try:
            oid = ObjectId(course_id)
        except Exception:
            return {"error": "Invalid ID"}, 400

        # Check if course exists before deleting.
        doc = db.find_one({"_id": oid})
        if not doc:
            return {"error": "Course not found"}, 404

        # Delete the course.
        db.delete_one({"_id": oid})

        deleted_json = to_json(doc)

        # Notify other services that a course was removed.
        publish_event("course_deleted", deleted_json)

        return {"message": "Course deleted", "course": deleted_json}, 200

    return app


# Entry point for running as a standalone service.
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)