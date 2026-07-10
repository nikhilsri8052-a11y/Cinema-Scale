import pandas as pd
import difflib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def load_and_train_model(csv_path="movies.csv"):
    """
    Loads the movie CSV dataset, handles null values by filling them with empty strings,
    combines specific features into a single string, fits a TfidfVectorizer on the combined features,
    and computes the cosine similarity matrix.
    
    Args:
        csv_path (str): The path to the CSV dataset file. Defaults to "movies.csv".
        
    Returns:
        tuple: (movies_data (pd.DataFrame), similarity (np.ndarray), list_of_all_titles (list))
    """
    try:
        # Load the CSV file
        movies_data = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV file from {csv_path}: {e}")
        # Return empty placeholders if loading fails
        return pd.DataFrame(), None, []

    # Features to combine
    selected_features = ['genres', 'keywords', 'tagline', 'cast', 'director']
    
    # Handle null values by filling them with empty strings
    for feature in selected_features:
        if feature in movies_data.columns:
            movies_data[feature] = movies_data[feature].fillna('')
        else:
            movies_data[feature] = ''

    # Combine the features into a single string for vectorization
    combined_features = (
        movies_data['genres'] + ' ' + 
        movies_data['keywords'] + ' ' + 
        movies_data['tagline'] + ' ' + 
        movies_data['cast'] + ' ' + 
        movies_data['director']
    )
    
    # Fit TfidfVectorizer on the combined features
    vectorizer = TfidfVectorizer()
    feature_vectors = vectorizer.fit_transform(combined_features)
    
    # Compute cosine similarity matrix
    similarity = cosine_similarity(feature_vectors)
    
    # Extract list of all movie titles
    list_of_all_titles = movies_data['title'].tolist()
    
    return movies_data, similarity, list_of_all_titles

def get_recommendations(movie_name, movies_data, similarity, list_of_all_titles, top_n=5):
    """
    Finds recommendations for a given movie title using cosine similarity scores.
    Handles typos in user input using difflib.
    
    Args:
        movie_name (str): Name of the movie to find recommendations for.
        movies_data (pd.DataFrame): Dataframe containing the movies.
        similarity (np.ndarray): Cosine similarity matrix.
        list_of_all_titles (list): List of all movie titles in the dataset.
        top_n (int): Number of recommendations to return. Defaults to 5.
        
    Returns:
        list: A list of dictionaries containing title and genres of recommended movies.
    """
    if movies_data.empty or similarity is None or not list_of_all_titles:
        return []

    # Use difflib to handle typos in movie names
    find_close_matches = difflib.get_close_matches(movie_name, list_of_all_titles)
    
    if not find_close_matches:
        return []
        
    close_match = find_close_matches[0]
    
    # Find the index of the closest match
    movie_indices = movies_data[movies_data.title == close_match].index
    if len(movie_indices) == 0:
        return []
    index_of_the_movie = movie_indices[0]
    
    # Enumerate the similarity scores for that movie index
    similarity_score = list(enumerate(similarity[index_of_the_movie]))
    
    # Sort similarity scores in reverse order (highest similarity first)
    sorted_similar_movies = sorted(similarity_score, key=lambda x: x[1], reverse=True)
    
    recommendations = []
    count = 0
    
    for item in sorted_similar_movies:
        index = item[0]
        # Ignore the movie itself
        if index == index_of_the_movie:
            continue
            
        row = movies_data.iloc[index]
        # Get title and genres
        title = row.get('title', 'Unknown')
        genres = row.get('genres', 'Unknown')
        
        recommendations.append({
            'title': title,
            'genres': genres
        })
        
        count += 1
        if count >= top_n:
            break
            
    return recommendations
