from .database import db

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
