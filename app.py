import os
import json
import math
from datetime import datetime, timezone
import pandas as pd
from flask import Flask, abort, redirect, render_template, request, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
from sqlalchemy import create_engine, text
from werkzeug.security import check_password_hash, generate_password_hash
from recommend import load_and_train_model, get_recommendations, fetch_tmdb_info, fetch_poster_by_tmdb_id, fetch_wikipedia_poster


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

db = SQLAlchemy(app)

# Load and train recommendation engine once on startup
print("Initializing movie recommendation system...")
movies_df, similarity_matrix, list_of_all_titles = load_and_train_model("movies.csv")
print("Recommendation system initialized successfully!")


# ============================================================
# DATABASE MODELS
# ============================================================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, default="user")
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

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
    poster_path = db.Column(db.String(500), nullable=True)
    
    # Deep Metadata Columns
    runtime = db.Column(db.Integer, nullable=True)
    budget = db.Column(db.BigInteger, nullable=True)
    revenue = db.Column(db.BigInteger, nullable=True)
    status = db.Column(db.String(100), nullable=True)
    original_language = db.Column(db.String(50), nullable=True)
    production_companies = db.Column(db.Text, nullable=True)
    production_countries = db.Column(db.Text, nullable=True)
    spoken_languages = db.Column(db.String(255), nullable=True)
    adult = db.Column(db.Boolean, default=False, nullable=True)
    popularity = db.Column(db.Float, nullable=True)
    vote_count = db.Column(db.Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<Movie {self.title}>"
    
    def to_card_dict(self):
        """Return dict for movie card rendering in JSON APIs."""
        return {
            'id': self.id,
            'title': self.title,
            'genre': self.genre,
            'year': self.year,
            'rating': self.rating,
            'poster_path': self.poster_path,
        }


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", backref=db.backref("reviews", lazy=True, cascade="all, delete-orphan"))
    movie = db.relationship("Movie", backref=db.backref("reviews", lazy=True, cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"<Review user_id={self.user_id} movie_id={self.movie_id} rating={self.rating}>"


class Like(db.Model):
    __tablename__ = "likes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", backref=db.backref("likes", lazy=True, cascade="all, delete-orphan"))
    movie = db.relationship("Movie", backref=db.backref("likes", lazy=True, cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint('user_id', 'movie_id', name='unique_user_movie_like'),)


class SavedMovie(db.Model):
    __tablename__ = "saved_movies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", backref=db.backref("saved_movies", lazy=True, cascade="all, delete-orphan"))
    movie = db.relationship("Movie", backref=db.backref("saved_by", lazy=True, cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint('user_id', 'movie_id', name='unique_user_movie_save'),)


# ============================================================
# CONTEXT PROCESSOR — inject user info into all templates
# ============================================================

@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    return {"current_user": user, "is_logged_in": bool(user), "is_admin": session.get("is_admin", False)}


# ============================================================
# DATABASE SEEDING
# ============================================================

def _safe_int(val, default=None):
    """Safely convert a value to int."""
    try:
        if pd.isna(val):
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default

def _safe_float(val, default=None):
    """Safely convert a value to float."""
    try:
        if pd.isna(val):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

def _safe_str(val, default=''):
    """Safely convert a value to string."""
    if pd.isna(val) or val is None:
        return default
    return str(val).strip()

def _parse_json_names(val):
    """Parse JSON-like string to extract 'name' fields."""
    if pd.isna(val) or not val:
        return ''
    try:
        items = json.loads(str(val).replace("'", '"'))
        if isinstance(items, list):
            return ', '.join([i.get('name', '') for i in items if i.get('name')])
    except (json.JSONDecodeError, AttributeError):
        pass
    return str(val)


def seed_database_from_csv(app):
    with app.app_context():
        # Recreate tables if empty
        db.create_all()

        # Seed default test users
        if db.session.query(User).count() == 0:
            admin_user = User(
                username="Admin",
                email="admin@movie.com",
                password_hash=generate_password_hash("admin123"),
                is_admin=True,
            )
            regular_user = User(
                username="TestUser",
                email="user@movie.com",
                password_hash=generate_password_hash("user123"),
                is_admin=False,
            )
            db.session.add_all([admin_user, regular_user])
            db.session.commit()

        # Seed Movie table if empty
        if db.session.query(Movie).count() == 0:
            print("Movie table is empty. Seeding from movies.csv...")
            csv_path = "movies.csv"
            if os.path.exists(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                    movies_to_insert = []
                    batch_size = 500
                    for idx, row in df.iterrows():
                        title = _safe_str(row.get('title'), 'Unknown')
                        if not title or title == 'Unknown':
                            continue
                        
                        # Parse year from release_date
                        rel_date = _safe_str(row.get('release_date'))
                        year = 2000
                        if rel_date and '-' in rel_date:
                            try:
                                year = int(rel_date.split('-')[0])
                            except ValueError:
                                pass
                        
                        genre = _safe_str(row.get('genres'), 'Drama')
                        plot = _safe_str(row.get('overview'), 'No overview available.')
                        rating = _safe_float(row.get('vote_average'), 0.0)
                        tmdb_id = _safe_str(row.get('id'))
                        
                        # Parse all available metadata from CSV
                        runtime = _safe_int(row.get('runtime'))
                        budget = _safe_int(row.get('budget'))
                        revenue = _safe_int(row.get('revenue'))
                        popularity = _safe_float(row.get('popularity'))
                        vote_count = _safe_int(row.get('vote_count'))
                        original_language = _safe_str(row.get('original_language'))
                        status = _safe_str(row.get('status'))
                        spoken_languages = _parse_json_names(row.get('spoken_languages'))
                        production_companies = _parse_json_names(row.get('production_companies'))
                        production_countries = _parse_json_names(row.get('production_countries'))

                        movie = Movie(
                            tmdb_id=tmdb_id,
                            title=title,
                            genre=genre,
                            year=year,
                            plot=plot if plot else 'No overview available.',
                            rating=rating,
                            poster_path=None,  # Will be fetched on-demand from TMDB
                            runtime=runtime,
                            budget=budget,
                            revenue=revenue,
                            status=status if status else None,
                            original_language=original_language if original_language else None,
                            production_companies=production_companies if production_companies else None,
                            production_countries=production_countries if production_countries else None,
                            spoken_languages=spoken_languages if spoken_languages else None,
                            adult=False,
                            popularity=popularity,
                            vote_count=vote_count
                        )
                        movies_to_insert.append(movie)

                        if len(movies_to_insert) >= batch_size:
                            db.session.add_all(movies_to_insert)
                            db.session.commit()
                            movies_to_insert = []

                    if movies_to_insert:
                        db.session.add_all(movies_to_insert)
                        db.session.commit()
                    print(f"Bulk seeding complete. Seeded {db.session.query(Movie).count()} movies.")
                except Exception as e:
                    print(f"Error seeding database from CSV: {e}")
                    db.session.rollback()


seed_database_from_csv(app)


# ============================================================
# HELPER — fetch and cache poster for a movie
# ============================================================

def ensure_poster(movie):
    """Fetch poster from TMDB if not cached, and save to DB."""
    if movie.poster_path:
        return False
    
    poster_url = None
    if movie.tmdb_id:
        poster_url = fetch_poster_by_tmdb_id(movie.tmdb_id)
        
    if not poster_url:
        # Fallback to Wikipedia search scraping
        poster_url = fetch_wikipedia_poster(movie.title, movie.year)
        
    if poster_url:
        movie.poster_path = poster_url
        return True
    return False


# ============================================================
# AUTH ROUTES
# ============================================================

@app.route("/auth", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        auth_mode = request.form.get("auth_mode", "login")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("auth.html", error="Email and password are required.")

        if auth_mode == "signup":
            username = request.form.get("username", "").strip()
            if not username:
                username = email.split("@")[0]

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return render_template("auth.html", error="An account with this email already exists.")

            # SECURITY: Always register as regular user, never admin
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_admin=False
            )
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            session["is_admin"] = False
            
            next_url = session.pop("next_url", None)
            return redirect(next_url or url_for("index"))

        # LOGIN mode
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return render_template("auth.html", error="Invalid email or password.")

        session["user_id"] = user.id
        session["is_admin"] = user.is_admin
        
        next_url = session.pop("next_url", None)
        return redirect(next_url or url_for("index"))

    if session.get("user_id"):
        return redirect(url_for("index"))

    return render_template("auth.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ============================================================
# MAIN PAGES
# ============================================================

@app.route("/", methods=["GET"])
def index():
    search_query = request.args.get("q", "").strip()
    updated = False
    if search_query:
        movies = Movie.query.filter(Movie.title.ilike(f"%{search_query}%")).order_by(Movie.rating.desc()).limit(20).all()
        # Fetch posters on-demand for search results
        for m in movies:
            if ensure_poster(m):
                updated = True
        if updated:
            try:
                db.session.commit()
            except sqlalchemy.exc.OperationalError:
                db.session.rollback()
        return render_template(
            "index.html",
            movies=movies,
            search_query=search_query,
            categorized_movies={}
        )

    # 1. Fetch data from DB first (avoids autoflush contention)
    trending_movies = Movie.query.order_by(Movie.rating.desc()).limit(4).all()

    genres = ["Drama", "Crime", "Thriller", "Action", "Adventure", "Animation", "Family", "Comedy", "Romance"]
    categorized_movies = {}
    for g in genres:
        movies_in_g = Movie.query.filter(Movie.genre.ilike(f"%{g}%")).order_by(Movie.rating.desc()).limit(4).all()
        if movies_in_g:
            categorized_movies[g] = movies_in_g

    # 2. Update poster paths in memory
    for m in trending_movies:
        if ensure_poster(m):
            updated = True

    for g, movies_in_g in categorized_movies.items():
        for m in movies_in_g:
            if ensure_poster(m):
                updated = True

    # 3. Commit changes once at the end (with safe rollback)
    if updated:
        try:
            db.session.commit()
        except sqlalchemy.exc.OperationalError:
            db.session.rollback()
            print("Database locked during index commit, rolled back safely.")

    return render_template(
        "index.html",
        movies=trending_movies,
        search_query=search_query,
        categorized_movies=categorized_movies
    )


@app.route("/category/<genre>")
def category(genre):
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    pagination = Movie.query.filter(Movie.genre.ilike(f"%{genre}%")).order_by(Movie.rating.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    updated = False
    # Fetch posters on-demand for movies listed on the current page
    for m in pagination.items:
        if ensure_poster(m):
            updated = True
            
    if updated:
        try:
            db.session.commit()
        except sqlalchemy.exc.OperationalError:
            db.session.rollback()
            print("Database locked during category commit, rolled back safely.")
            
    return render_template("category.html", genre=genre, pagination=pagination)


@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id: int):
    movie = Movie.query.get_or_404(movie_id)

    # ON-DEMAND API TRIGGER: Fetch deep metadata if not already cached
    if movie.poster_path is None or movie.runtime is None:
        tmdb_data = fetch_tmdb_info(movie.title)
        if tmdb_data.get('poster_path'):
            movie.poster_path = tmdb_data['poster_path']
        
        if not movie.poster_path:
            movie.poster_path = fetch_wikipedia_poster(movie.title, movie.year)
        if tmdb_data.get('overview') and (not movie.plot or movie.plot == "No overview available."):
            movie.plot = tmdb_data['overview']
        
        if movie.runtime is None:
            movie.runtime = tmdb_data.get('runtime')
        if movie.budget is None:
            movie.budget = tmdb_data.get('budget')
        if movie.revenue is None:
            movie.revenue = tmdb_data.get('revenue')
        if movie.status is None:
            movie.status = tmdb_data.get('status')
        if movie.original_language is None:
            movie.original_language = tmdb_data.get('original_language')
        if movie.production_companies is None:
            movie.production_companies = tmdb_data.get('production_companies')
        if movie.production_countries is None:
            movie.production_countries = tmdb_data.get('production_countries')
        if movie.spoken_languages is None:
            movie.spoken_languages = tmdb_data.get('spoken_languages')
        if movie.popularity is None:
            movie.popularity = tmdb_data.get('popularity')
        if movie.vote_count is None:
            movie.vote_count = tmdb_data.get('vote_count')
        if tmdb_data.get('vote_average') and tmdb_data['vote_average'] > 0:
            movie.rating = tmdb_data['vote_average']
        try:
            db.session.commit()
        except sqlalchemy.exc.OperationalError:
            db.session.rollback()
            print("Database locked during movie_detail commit, rolled back safely.")

    # ML ENGINE TRIGGER: Query database for top 10 recommended movie titles
    raw_recommendations = get_recommendations(movie.title, movies_df, similarity_matrix, list_of_all_titles, top_n=10)
    
    similar_movies = []
    for rec in raw_recommendations:
        db_movie = Movie.query.filter_by(title=rec['title']).first()
        if db_movie:
            ensure_poster(db_movie)
            similar_movies.append(db_movie)

    # Dynamically generate analytics based on rating metric
    critic_score = int(movie.rating * 10)
    audience_score = round(movie.rating / 2.0, 1)
    pop_rank = max(1, int(100 - (movie.rating * 10)))
    
    analytics = {
        "popularity": pop_rank,
        "engagement": int(movie.rating * 10.5),
        "audience_rating": audience_score,
        "critic_rating": critic_score,
        "labels": ["Views", "Likes", "Shares", "Watch Time"],
        "values": [int(movie.rating * 8), int(movie.rating * 7), int(movie.rating * 5), int(movie.rating * 9)],
    }

    # Extract director and cast from movies_df if available
    director = "N/A"
    cast = "N/A"
    row_matches = movies_df[movies_df.title == movie.title]
    if not row_matches.empty:
        row = row_matches.iloc[0]
        raw_director = row.get('director')
        raw_cast = row.get('cast')
        if pd.notna(raw_director) and raw_director:
            director = raw_director
        if pd.notna(raw_cast) and raw_cast:
            cast = raw_cast

    # Fetch all user reviews for this movie
    reviews = Review.query.filter_by(movie_id=movie.id).order_by(Review.timestamp.desc()).all()

    # Check if current user has liked/saved this movie
    user_liked = False
    user_saved = False
    if session.get("user_id"):
        user_liked = Like.query.filter_by(user_id=session["user_id"], movie_id=movie.id).first() is not None
        user_saved = SavedMovie.query.filter_by(user_id=session["user_id"], movie_id=movie.id).first() is not None

    return render_template(
        "movie_info.html", 
        movie=movie, 
        analytics=analytics, 
        similar_movies=similar_movies,
        director=director,
        cast=cast,
        reviews=reviews,
        user_liked=user_liked,
        user_saved=user_saved,
        like_count=Like.query.filter_by(movie_id=movie.id).count()
    )


# ============================================================
# USER INTERACTION ROUTES (Like, Save, Review)
# ============================================================

@app.route("/movie/<int:movie_id>/like", methods=["POST"])
def toggle_like(movie_id: int):
    if not session.get("user_id"):
        session["next_url"] = url_for("movie_detail", movie_id=movie_id)
        return redirect(url_for("auth"))
    
    existing = Like.query.filter_by(user_id=session["user_id"], movie_id=movie_id).first()
    if existing:
        db.session.delete(existing)
    else:
        like = Like(user_id=session["user_id"], movie_id=movie_id)
        db.session.add(like)
    db.session.commit()
    return redirect(url_for("movie_detail", movie_id=movie_id))


@app.route("/movie/<int:movie_id>/save", methods=["POST"])
def toggle_save(movie_id: int):
    if not session.get("user_id"):
        session["next_url"] = url_for("movie_detail", movie_id=movie_id)
        return redirect(url_for("auth"))
    
    existing = SavedMovie.query.filter_by(user_id=session["user_id"], movie_id=movie_id).first()
    if existing:
        db.session.delete(existing)
    else:
        save = SavedMovie(user_id=session["user_id"], movie_id=movie_id)
        db.session.add(save)
    db.session.commit()
    return redirect(url_for("movie_detail", movie_id=movie_id))


@app.route("/movie/<int:movie_id>/review", methods=["POST"])
def submit_review(movie_id: int):
    if not session.get("user_id"):
        session["next_url"] = url_for("movie_detail", movie_id=movie_id)
        return redirect(url_for("auth"))

    rating = request.form.get("rating")
    comment = request.form.get("comment", "").strip()

    if not rating:
        return redirect(url_for("movie_detail", movie_id=movie_id))

    try:
        rating_int = int(rating)
        rating_int = max(1, min(10, rating_int))
    except ValueError:
        return redirect(url_for("movie_detail", movie_id=movie_id))

    review = Review(
        user_id=session["user_id"],
        movie_id=movie_id,
        rating=rating_int,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()

    return redirect(url_for("movie_detail", movie_id=movie_id))


# ============================================================
# USER PROFILE
# ============================================================

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("auth"))
    
    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("auth"))
    
    updated = False
    # Get liked movies
    liked_movies = db.session.query(Movie).join(Like).filter(Like.user_id == user.id).order_by(Like.timestamp.desc()).all()
    for m in liked_movies:
        if ensure_poster(m):
            updated = True
    
    # Get saved movies
    saved_movies = db.session.query(Movie).join(SavedMovie).filter(SavedMovie.user_id == user.id).order_by(SavedMovie.timestamp.desc()).all()
    for m in saved_movies:
        if ensure_poster(m):
            updated = True
            
    if updated:
        try:
            db.session.commit()
        except sqlalchemy.exc.OperationalError:
            db.session.rollback()
            print("Database locked during profile commit, rolled back safely.")
    
    # Get user reviews
    user_reviews = Review.query.filter_by(user_id=user.id).order_by(Review.timestamp.desc()).all()
    
    return render_template(
        "profile.html",
        user=user,
        liked_movies=liked_movies,
        saved_movies=saved_movies,
        user_reviews=user_reviews
    )


# ============================================================
# API ROUTES (JSON for AJAX load-more)
# ============================================================

@app.route("/api/movies/<genre>")
def api_movies_by_genre(genre):
    """Returns paginated movies for a genre as JSON for AJAX load-more."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    pagination = Movie.query.filter(Movie.genre.ilike(f"%{genre}%")).order_by(Movie.rating.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    for m in pagination.items:
        ensure_poster(m)
    
    return jsonify({
        'movies': [m.to_card_dict() for m in pagination.items],
        'has_next': pagination.has_next,
        'page': pagination.page,
        'total_pages': pagination.pages
    })


# ============================================================
# ADMIN ROUTES
# ============================================================

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
                users=User.query.order_by(User.id.desc()).all(),
                movies_list=Movie.query.order_by(Movie.id.desc()).limit(50).all(),
                user_count=User.query.count(),
                movie_count=Movie.query.count(),
                review_count=Review.query.count(),
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
        users=User.query.order_by(User.id.desc()).all(),
        movies_list=Movie.query.order_by(Movie.id.desc()).limit(50).all(),
        user_count=User.query.count(),
        movie_count=Movie.query.count(),
        review_count=Review.query.count(),
    )


@app.route("/admin/delete-user/<int:user_id>", methods=["POST"])
def admin_delete_user(user_id: int):
    if not session.get("is_admin"):
        abort(403)
    
    user = User.query.get_or_404(user_id)
    # Prevent admin from deleting themselves
    if user.id == session.get("user_id"):
        return redirect(url_for("admin"))
    
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/delete-movie/<int:movie_id>", methods=["POST"])
def admin_delete_movie(movie_id: int):
    if not session.get("is_admin"):
        abort(403)
    
    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True)
