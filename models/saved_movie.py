from datetime import datetime, timezone
from .database import db

class SavedMovie(db.Model):
    __tablename__ = "saved_movies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", backref=db.backref("saved_movies", lazy=True, cascade="all, delete-orphan"))
    movie = db.relationship("Movie", backref=db.backref("saved_by", lazy=True, cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint('user_id', 'movie_id', name='unique_user_movie_save'),)
