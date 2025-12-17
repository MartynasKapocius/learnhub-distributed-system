# mongo.py
from pymongo import MongoClient
import certifi
import os
import logging

logger = logging.getLogger(__name__)

_mongo_client = None

MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_HOST = os.getenv("MONGO_HOST")

def get_mongo_client():
    """
    Lazy, safe MongoDB client.
    Works in local, Docker, VM, CI.
    """
    global _mongo_client

    if _mongo_client is not None:
        return _mongo_client
    
    MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}/?appName=ds&tlsAllowInvalidCertificates=true"

    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not set")

    try:
        _mongo_client = MongoClient(
            MONGO_URI,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
        )

        _mongo_client.admin.command("ping")
        logger.info("MongoDB connected successfully")

    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        _mongo_client = None

    return _mongo_client
