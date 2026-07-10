from datetime import datetime, timezone
from .database import db

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
