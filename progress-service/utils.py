def compute_progress_metrics(attempts):
    """
    attempts: list of dicts with fields:
      score (int), timestamp (str), quiz_id (int)

    returns: dict containing:
      total_attempts, last_score, best_score, average_score, improvement_percentage
    """
    if not attempts:
        return {
            "total_attempts": 0,
            "last_score": None,
            "best_score": None,
            "average_score": None,
            "improvement_percentage": None
        }

    total_attempts = len(attempts)
    last_score = attempts[-1]["score"]
    best_score = max(a["score"] for a in attempts)
    average_score = sum(a["score"] for a in attempts) / total_attempts

    first_score = attempts[0]["score"]
    if first_score == 0:
        improvement_percentage = None
    else:
        improvement_percentage = (last_score - first_score) / first_score * 100

    return {
        "total_attempts": total_attempts,
        "last_score": last_score,
        "best_score": best_score,
        "average_score": round(average_score, 2),
        "improvement_percentage": round(improvement_percentage, 2) if improvement_percentage else 0,
    }
