import os
from flask import Flask, session
from sqlalchemy import create_engine, text
from models import db, User
from helpers.seeding import seed_database_from_csv
from services.recommendation import load_and_train_model
from routes import register_routes

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JSON_SORT_KEYS"] = False

def resolve_database_uri():
    configured_uri = os.environ.get("DATABASE_URL", "postgresql://username:password@localhost:5432/moviedb")
    if os.environ.get("USE_SQLITE") == "1":
        return "sqlite:///movie_app.db"

    if configured_uri.startswith("postgresql"):
        try:
            engine = create_engine(configured_uri)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return configured_uri
        except Exception:
            return "sqlite:///movie_app.db"

    return configured_uri

app.config["SQLALCHEMY_DATABASE_URI"] = resolve_database_uri()
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"timeout": 30}
}

# Bind SQLAlchemy to Flask App
db.init_app(app)

# Load and train recommendation engine once on startup
print("Initializing movie recommendation system...")
movies_df, similarity_matrix, list_of_all_titles = load_and_train_model("movies.csv")
print("Recommendation system initialized successfully!")

# Seed database
seed_database_from_csv(app)

# Context processor — inject user info into all templates
@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    return {"current_user": user, "is_logged_in": bool(user), "is_admin": session.get("is_admin", False)}

# Register routes
register_routes(app, movies_df, similarity_matrix, list_of_all_titles)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
