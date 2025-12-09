from fastapi import FastAPI
from pymongo import MongoClient
from bson.json_util import dumps
import os

app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
client = MongoClient(MONGO_URI)
db = client["progress_db"]
progress_col = db["progress"]

@app.get("/progress/{user_id}/{quiz_id}")
def get_progress(user_id: str, quiz_id: str):
    result = progress_col.find_one({"user_id": user_id, "quiz_id": quiz_id})

    if not result:
        return {"message": "No progress data yet"}

    return {
        "average_score": result.get("average_score"),
        "highest_score": result.get("max_score"),
        "recent_score": result.get("recent_score"),
        "attempts": result.get("attempts"),
        "improvement": result.get("improvement")
    }

