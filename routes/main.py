from flask import render_template, request, session, url_for, redirect, abort
import sqlalchemy
import pandas as pd
from models import db, Movie, User, Review, Like, SavedMovie
from helpers.posters import ensure_poster, fetch_tmdb_info, fetch_wikipedia_poster
from services.recommendation import get_recommendations

def register_main_routes(app, movies_df, similarity_matrix, list_of_all_titles):
    @app.route("/", methods=["GET"])
    def index():
        search_query = request.args.get("q", "").strip()
        genre_filter = request.args.get("genre", "").strip()
        year_min = request.args.get("year_min", "", type=str).strip()
        year_max = request.args.get("year_max", "", type=str).strip()
        rating_min = request.args.get("rating_min", "", type=str).strip()
        language_filter = request.args.get("language", "").strip()
        updated = False

        # Collect available genres and languages for the filter dropdowns
        all_genres = ["Action", "Adventure", "Animation", "Comedy", "Crime", "Drama",
                      "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
                      "Romance", "Science Fiction", "Thriller", "War", "Western"]
        all_languages = db.session.query(Movie.original_language).filter(
            Movie.original_language.isnot(None),
            Movie.original_language != ''
        ).distinct().order_by(Movie.original_language).all()
        all_languages = sorted(set(lang[0].strip() for lang in all_languages if lang[0] and lang[0].strip()))

        # Check if any filter is active
        has_filters = any([search_query, genre_filter, year_min, year_max, rating_min, language_filter])

        if has_filters:
            query = Movie.query
            if search_query:
                query = query.filter(Movie.title.ilike(f"%{search_query}%"))
            if genre_filter:
                query = query.filter(Movie.genre.ilike(f"%{genre_filter}%"))
            if year_min:
                try:
                    query = query.filter(Movie.year >= int(year_min))
                except ValueError:
                    pass
            if year_max:
                try:
                    query = query.filter(Movie.year <= int(year_max))
                except ValueError:
                    pass
            if rating_min:
                try:
                    query = query.filter(Movie.rating >= float(rating_min))
                except ValueError:
                    pass
            if language_filter:
                query = query.filter(Movie.original_language == language_filter)

            movies = query.order_by(Movie.rating.desc()).limit(40).all()
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
                genre_filter=genre_filter,
                year_min=year_min,
                year_max=year_max,
                rating_min=rating_min,
                language_filter=language_filter,
                all_genres=all_genres,
                all_languages=all_languages,
                categorized_movies={}
            )

        # 1. Fetch data from DB first
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

        # 3. Commit changes once at the end
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
            genre_filter=genre_filter,
            year_min=year_min,
            year_max=year_max,
            rating_min=rating_min,
            language_filter=language_filter,
            all_genres=all_genres,
            all_languages=all_languages,
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
        if not movies_df.empty:
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
