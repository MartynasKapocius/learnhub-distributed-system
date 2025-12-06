import json
import os
import time
import logging
from datetime import datetime

import pika
from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError
from tenacity import retry, wait_exponential, stop_after_attempt

from utils import compute_progress_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("progress_worker")

# --------------------------
# Environment Variables
# --------------------------
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/progress_service")

EXCHANGE_NAME = "quiz_events"
ROUTING_KEY = "quiz.submitted"
QUEUE_NAME = "progress_queue"

# --------------------------
# Setup MongoDB
# --------------------------
mongo_client = MongoClient(MONGO_URI, socketTimeoutMS=5000)
db = mongo_client.get_database()
progress_col = db["progress"]

# secure that same one user+one course has one progress record
progress_col.create_index(
    [("user_id", ASCENDING), ("course_id", ASCENDING)],
    unique=True
)


# --------------------------
# Helpers
# --------------------------
def parse_event(body):
    """Parse the quiz_submitted event."""
    try:
        data = json.loads(body.decode("utf-8"))
        required = ["user_id", "course_id", "quiz_id", "score", "timestamp"]
        for f in required:
            if f not in data:
                raise ValueError(f"Missing field {f}")
        return data
    except Exception as e:
        raise ValueError(f"Failed to parse event: {e}")


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1, max=10))
def update_progress(event):
    """Use retry for resilience."""

    user_id = event["user_id"]
    course_id = event["course_id"]
    quiz_id = event["quiz_id"]
    score = event["score"]
    timestamp = event["timestamp"]

    logger.info(f"Updating progress for user={user_id}, course={course_id}")

    # get the current progress record
    progress = progress_col.find_one({"user_id": user_id, "course_id": course_id})

    if not progress:
        attempts = []
    else:
        attempts = progress.get("attempts", [])

    # if the timestamp exists, jump it
    if any(a["timestamp"] == timestamp for a in attempts):
        logger.info("Duplicate event detected — skipping")
        return

    # Append new attempt
    attempts.append({
        "quiz_id": quiz_id,
        "score": score,
        "timestamp": timestamp
    })

    # calculate the metrics
    metrics = compute_progress_metrics(attempts)

    update_doc = {
        "$set": {
            "user_id": user_id,
            "course_id": course_id,
            "attempts": attempts,
            "total_attempts": metrics["total_attempts"],
            "last_score": metrics["last_score"],
            "best_score": metrics["best_score"],
            "average_score": metrics["average_score"],
            "improvement_percentage": metrics["improvement_percentage"],
            "updated_at": datetime.utcnow().isoformat()
        }
    }

    progress_col.update_one(
        {"user_id": user_id, "course_id": course_id},
        update_doc,
        upsert=True
    )

    logger.info("Progress updated successfully.")


def on_message(channel, method, properties, body):
    """RabbitMQ consumer callback."""
    try:
        event = parse_event(body)
        logger.info(f"Received event: {event}")

        update_progress(event)   # With retry logic

        channel.basic_ack(delivery_tag=method.delivery_tag)

    except ValueError as e:
        logger.error(f"Bad event — discarding: {e}")
        channel.basic_ack(delivery_tag=method.delivery_tag)

    except PyMongoError as e:
        logger.error(f"Database error, requeueing event: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    except Exception as e:
        logger.error(f"Unexpected error, requeueing: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def start_worker():
    logger.info("Progress Worker starting…")

    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()

            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE_NAME, routing_key=ROUTING_KEY)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)

            logger.info("Waiting for quiz.submitted events…")
            channel.start_consuming()

        except Exception as e:
            logger.error(f"Worker crashed, reconnecting in 5 sec: {e}")
            time.sleep(5)


if __name__ == "__main__":
    start_worker()
