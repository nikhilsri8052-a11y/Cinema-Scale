import os
import json
import pandas as pd
from werkzeug.security import generate_password_hash
from models import db, User, Movie

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
