from fastapi import FastAPI
from pymongo import MongoClient
from bson.json_util import dumps
from dotenv import load_dotenv
import os
load_dotenv()

app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
client = MongoClient(MONGO_URI)
db = client[os.getenv("DATABASE_NAME", "LearnHubDB")]
progress_col = db["progress"]


@app.get("/progress/{user_id}/{course_id}/{quiz_id}")
def get_progress(user_id: str, course_id: str, quiz_id: str):
    
    result = progress_col.find_one({
        "user_id": user_id,
        "course_id": course_id,
        "quiz_id": int(quiz_id)
    })

    if not result:
        return {"message": "No progress data yet"}

    attempts = result.get("attempts", [])
    scores = [a.get("score", 0) for a in attempts]

    return {
        "user_id": user_id,
        "course_id": course_id,
        "quiz_id": quiz_id,
        "average_score": result.get("average_score"),
        "highest_score": result.get("best_score"),
        "recent_score": result.get("last_score"),
        "attempts": len(attempts),
        "improvement": result.get("improvement_percentage"),
        "attempt_details": attempts
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)
