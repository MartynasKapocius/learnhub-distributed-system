from flask import current_app
from extensions import mongo

def get_db():
    """
    Return an active database instance.

    This function supports both App Factory and Blueprint import order.
    In Flask applications using factory patterns, `mongo.db` may be None
    when modules are imported before `mongo.init_app(app)` is executed.

    Therefore:
    - If `mongo.db` is available, use it because PyMongo has already been initialized.
    - If `mongo.db` is None, fall back to using `mongo.cx[database_name]`,
      which always works because the underlying MongoClient (`cx`) is created immediately.
    """

    # Normal case: PyMongo has been initialized and a bound database is available
    if mongo.db is not None:
        return mongo.db

    # Fallback case: PyMongo not yet fully initialized when imported (common with blueprints)
    # Use raw client (`mongo.cx`) with explicit database name
    db_name = current_app.config.get("DATABASE_NAME", "LearnHubDB")
    return mongo.cx[db_name]

def get_users_col():
    return get_db()["users"]

def get_courses_col():
    return get_db()["courses"]
