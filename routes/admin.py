from flask import render_template, request, session, abort, redirect, url_for
from models import db, User, Movie, Review

def register_admin_routes(app):
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
