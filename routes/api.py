from flask import request, jsonify
from models import Movie
from helpers.posters import ensure_poster

def register_api_routes(app):
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
