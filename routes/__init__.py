def register_routes(app, movies_df, similarity_matrix, list_of_all_titles):
    from .auth import register_auth_routes
    from .main import register_main_routes
    from .interactions import register_interaction_routes
    from .admin import register_admin_routes
    from .api import register_api_routes
    
    register_auth_routes(app)
    register_main_routes(app, movies_df, similarity_matrix, list_of_all_titles)
    register_interaction_routes(app)
    register_admin_routes(app)
    register_api_routes(app)
