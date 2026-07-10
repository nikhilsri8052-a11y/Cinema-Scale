from flask import request, session, url_for, redirect
from models import db, Like, SavedMovie, Review

def register_interaction_routes(app):
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
