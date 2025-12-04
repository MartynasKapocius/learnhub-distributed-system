# Importing.
import os
import json
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import pika


# Course Service.
def create_app():
    app = Flask(__name__)

    # Basic configuration.
    app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://mongo:27017/learnhub_dev")
    app.config["RABBITMQ_HOST"] = os.getenv("RABBITMQ_HOST", "rabbitmq")
    app.config["EVENT_EXCHANGE"] = os.getenv("EVENT_EXCHANGE", "learning_events")

    # MongoDB client and collection.
    mongo_client = MongoClient(app.config["MONGO_URI"])
    db = mongo_client.get_default_database()
    course_col = db["courses"]

    print(f"[Course Service] Connected to MongoDB: {app.config['MONGO_URI']}")

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
        return {
            "id": str(doc["_id"]),
            "title": doc.get("title"),
            "description": doc.get("description", "")
        }

    # Health check used by Docker/K8s.
    @app.get("/health")
    def health():
        try:
            count = course_col.estimated_document_count()
            return {"status": "ok", "db": "ok", "count": count}
        except Exception as e:
            app.logger.error(f"Health check DB error: {e}")
            return {"status": "error", "db": "unreachable"}, 500

    # Get all courses.
    @app.get("/courses")
    def get_courses():
        docs = list(course_col.find())
        return jsonify([to_json(d) for d in docs]), 200

    # Get a single course by ID.
    @app.get("/courses/<course_id>")
    def get_course(course_id):
        try:
            oid = ObjectId(course_id)
        except Exception:
            return {"error": "Invalid ID"}, 400

        doc = course_col.find_one({"_id": oid})
        if not doc:
            return {"error": "Course not found"}, 404

        return jsonify(to_json(doc)), 200

    # Create a new course.
    @app.post("/courses")
    def create_course():
        data = request.get_json() or {}
        title = data.get("title")
        description = data.get("description", "")

        if not title:
            return {"error": "title is required"}, 400

        result = course_col.insert_one({
            "title": title,
            "description": description
        })

        created = course_col.find_one({"_id": result.inserted_id})
        course_json = to_json(created)

        # This is where the service becomes event driven.
        publish_event("course_created", course_json)

        return jsonify(course_json), 201

    # Update an existing course.
    @app.put("/courses/<course_id>")
    def update_course(course_id):
        data = request.get_json() or {}

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
        result = course_col.update_one({"_id": oid}, {"$set": update_fields})

        # Document does not exist.
        if result.matched_count == 0:
            return {"error": "Course not found"}, 404

        # Fetch updated record.
        updated = course_col.find_one({"_id": oid})
        updated_json = to_json(updated)

        # Notify other services.
        publish_event("course_updated", updated_json)

        return jsonify(updated_json), 200

    # Delete an existing course.
    @app.delete("/courses/<course_id>")
    def delete_course(course_id):
        # Validate ObjectId.
        try:
            oid = ObjectId(course_id)
        except Exception:
            return {"error": "Invalid ID"}, 400

        # Check if course exists before deleting.
        doc = course_col.find_one({"_id": oid})
        if not doc:
            return {"error": "Course not found"}, 404

        # Delete the course.
        course_col.delete_one({"_id": oid})

        deleted_json = to_json(doc)

        # Notify other services that a course was removed.
        publish_event("course_deleted", deleted_json)

        return {"message": "Course deleted", "course": deleted_json}, 200

    return app


# Entry point for running as a standalone service.
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)