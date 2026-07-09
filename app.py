import os
from flask import Flask, abort, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from werkzeug.security import check_password_hash, generate_password_hash


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

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Movie(db.Model):
    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.String(100), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    plot = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Float, nullable=False)

    def __repr__(self) -> str:
        return f"<Movie {self.title}>"


@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    user = User.query.get(user_id) if user_id else None
    return {"current_user": user, "is_logged_in": bool(user)}


def seed_database():
    with app.app_context():
        db.create_all()

        if User.query.count() == 0 and Movie.query.count() == 0:
            admin_user = User(
                email="admin@movie.com",
                password_hash=generate_password_hash("admin123"),
                is_admin=True,
            )
            regular_user = User(
                email="user@movie.com",
                password_hash=generate_password_hash("user123"),
                is_admin=False,
            )

            movies = [
                Movie(
                    tmdb_id="101",
                    title="Neon Horizon",
                    genre="Sci-Fi",
                    year=2024,
                    plot="A daring astronaut returns to Earth with a mysterious signal that rewrites human history.",
                    rating=8.7,
                ),
                Movie(
                    tmdb_id="102",
                    title="Midnight Echoes",
                    genre="Thriller",
                    year=2023,
                    plot="A radio host uncovers a hidden conspiracy while investigating midnight broadcasts.",
                    rating=7.8,
                ),
                Movie(
                    tmdb_id="103",
                    title="Sunset Avenue",
                    genre="Drama",
                    year=2022,
                    plot="Two estranged siblings reunite in their hometown and face the truth about their past.",
                    rating=8.2,
                ),
                Movie(
                    tmdb_id="104",
                    title="Velvet Circuit",
                    genre="Romance",
                    year=2025,
                    plot="A talented coder falls for a street musician while building a citywide network of shared stories.",
                    rating=7.5,
                ),
                Movie(
                    tmdb_id="105",
                    title="Shadow of the Harbor",
                    genre="Crime",
                    year=2021,
                    plot="A former detective returns to the waterfront to solve the case of a missing journalist.",
                    rating=8.1,
                ),
                Movie(
                    tmdb_id="106",
                    title="Golden Summer",
                    genre="Comedy",
                    year=2020,
                    plot="A group of friends reopens a forgotten beach resort and accidentally changes their town forever.",
                    rating=7.3,
                ),
            ]

            db.session.add_all([admin_user, regular_user, *movies])
            db.session.commit()


seed_database()


@app.route("/auth", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        auth_mode = request.form.get("auth_mode", "login")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("auth.html", error="Email and password are required.")

        if auth_mode == "signup":
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return render_template("auth.html", error="An account with this email already exists.")

            user = User(email=email, password_hash=generate_password_hash(password), is_admin=False)
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            session["is_admin"] = user.is_admin
            return redirect(url_for("index"))

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return render_template("auth.html", error="Invalid email or password.")

        session["user_id"] = user.id
        session["is_admin"] = user.is_admin
        return redirect(url_for("index"))

    if session.get("user_id"):
        return redirect(url_for("index"))

    return render_template("auth.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth"))


@app.route("/", methods=["GET"])
def index():
    if not session.get("user_id"):
        return redirect(url_for("auth"))

    search_query = request.args.get("q", "").strip()
    if search_query:
        movies = Movie.query.filter(Movie.title.ilike(f"%{search_query}%")).order_by(Movie.rating.desc()).all()
    else:
        movies = Movie.query.order_by(Movie.rating.desc()).all()

    return render_template("index.html", movies=movies, search_query=search_query)


@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id: int):
    if not session.get("user_id"):
        return redirect(url_for("auth"))

    movie = Movie.query.get_or_404(movie_id)

    # TMDB API FETCH PLACEHOLDER
    analytics = {
        "popularity": 84,
        "engagement": 91,
        "audience_rating": 4.6,
        "critic_rating": 88,
        "labels": ["Views", "Likes", "Shares", "Watch Time"],
        "values": [72, 64, 43, 88],
    }

    return render_template("movie_info.html", movie=movie, analytics=analytics)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("is_admin"):
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        genre = request.form.get("genre", "").strip()
        year = request.form.get("year", "")
        rating = request.form.get("rating", "")
        plot = request.form.get("plot", "").strip()

        if not all([title, genre, year, rating, plot]):
            return render_template(
                "admin.html",
                user_count=User.query.count(),
                movie_count=Movie.query.count(),
                error="Please fill in all fields before adding a movie.",
            )

        movie = Movie(
            title=title,
            genre=genre,
            year=int(year),
            rating=float(rating),
            plot=plot,
            tmdb_id=None,
        )
        db.session.add(movie)
        db.session.commit()

        return redirect(url_for("admin"))

    return render_template(
        "admin.html",
        user_count=User.query.count(),
        movie_count=Movie.query.count(),
    )


if __name__ == "__main__":
    app.run(debug=True)
