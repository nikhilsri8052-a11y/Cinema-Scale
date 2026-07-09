import pandas as pd
import difflib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests

# Global variable for TMDB API Key
TMDB_API_KEY = "4eaafd6f0cb8a191ea04a640257556c8"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

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
    # We join with a space to keep them separated as distinct words
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
        # Ignore the movie itself (typically index 0 in sorted list, but check by index)
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


def fetch_poster_by_tmdb_id(tmdb_id):
    """
    Fetches the poster URL directly using a TMDB movie ID.
    Much faster than searching by title since it's a direct lookup.
    
    Args:
        tmdb_id (str or int): The TMDB movie ID.
        
    Returns:
        str or None: Full poster URL or None if not found.
    """
    if not TMDB_API_KEY or TMDB_API_KEY == "YOUR_API_KEY_HERE":
        return None
    if not tmdb_id or str(tmdb_id).strip() == '' or str(tmdb_id) == 'nan':
        return None

    try:
        detail_url = f"https://api.themoviedb.org/3/movie/{int(float(str(tmdb_id)))}"
        params = {'api_key': TMDB_API_KEY}
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        resp = requests.get(detail_url, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            poster = data.get('poster_path')
            if poster:
                return f"{IMAGE_BASE_URL}{poster}"
    except Exception as e:
        print(f"TMDB poster fetch failed for ID '{tmdb_id}': {e}")
    
    return None


def fetch_tmdb_info(movie_title):
    """
    Queries TMDB Search API in two steps:
    1. Search movie by title to get the TMDB ID.
    2. Query detail API with TMDB ID to get deep metadata.
    """
    fallback_data = {
        'poster_path': None,
        'overview': "Plot summary unavailable.",
        'release_date': "N/A",
        'runtime': None,
        'genres': "N/A",
        'budget': None,
        'revenue': None,
        'status': "N/A",
        'original_language': "N/A",
        'production_companies': "N/A",
        'production_countries': "N/A",
        'spoken_languages': "N/A",
        'adult': False,
        'popularity': 0.0,
        'vote_average': 0.0,
        'vote_count': 0
    }
    
    if not TMDB_API_KEY or TMDB_API_KEY == "YOUR_API_KEY_HERE":
        return fallback_data
        
    search_url = "https://api.themoviedb.org/3/search/movie"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # Step 1: Search movie to get ID
        search_params = {
            'api_key': TMDB_API_KEY,
            'query': movie_title
        }
        search_resp = requests.get(search_url, params=search_params, headers=headers, timeout=5)
        if search_resp.status_code == 200:
            search_data = search_resp.json()
            results = search_data.get('results', [])
            if results:
                movie_id = results[0].get('id')
                if movie_id:
                    # Step 2: Get detailed movie details
                    detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
                    detail_params = {
                        'api_key': TMDB_API_KEY
                    }
                    detail_resp = requests.get(detail_url, params=detail_params, headers=headers, timeout=5)
                    if detail_resp.status_code == 200:
                        movie = detail_resp.json()
                        
                        # Parse comma-separated strings
                        genres_list = [g.get('name') for g in movie.get('genres', []) if g.get('name')]
                        genres_str = ", ".join(genres_list) if genres_list else "N/A"
                        
                        companies_list = [c.get('name') for c in movie.get('production_companies', []) if c.get('name')]
                        companies_str = ", ".join(companies_list) if companies_list else "N/A"
                        
                        countries_list = [c.get('name') for c in movie.get('production_countries', []) if c.get('name')]
                        countries_str = ", ".join(countries_list) if countries_list else "N/A"
                        
                        langs_list = [l.get('english_name') or l.get('name') for l in movie.get('spoken_languages', []) if l.get('english_name') or l.get('name')]
                        langs_str = ", ".join(langs_list) if langs_list else "N/A"
                        
                        poster = movie.get('poster_path')
                        full_poster_url = f"{IMAGE_BASE_URL}{poster}" if poster else None
                        
                        return {
                            'poster_path': full_poster_url,
                            'overview': movie.get('overview') or "Plot summary unavailable.",
                            'release_date': movie.get('release_date') or "N/A",
                            'runtime': movie.get('runtime'),
                            'genres': genres_str,
                            'budget': movie.get('budget'),
                            'revenue': movie.get('revenue'),
                            'status': movie.get('status') or "N/A",
                            'original_language': movie.get('original_language') or "N/A",
                            'production_companies': companies_str,
                            'production_countries': countries_str,
                            'spoken_languages': langs_str,
                            'adult': bool(movie.get('adult', False)),
                            'popularity': float(movie.get('popularity') or 0.0),
                            'vote_average': float(movie.get('vote_average') or 0.0),
                            'vote_count': int(movie.get('vote_count') or 0)
                        }
    except Exception as e:
        print(f"TMDB deep metadata request failed for '{movie_title}': {e}")
        
    return fallback_data


def fetch_wikipedia_poster(movie_title, year=None):
    """
    Fetches the poster URL of a movie directly from Wikipedia's uploads CDN
    using Wikipedia's open query APIs. Excellent fallback for blocked environments.
    """
    import urllib.parse
    headers = {'User-Agent': 'CinemaScaleApp/1.0 (nikhilsri8052@gmail.com)'}
    
    # 1. Build search query
    search_query = f"{movie_title}"
    if year:
        search_query += f" {year} film"
    else:
        search_query += " film"
        
    search_url = "https://en.wikipedia.org/w/api.php"
    search_params = {
        'action': 'query',
        'list': 'search',
        'srsearch': search_query,
        'format': 'json'
    }
    
    try:
        r = requests.get(search_url, params=search_params, headers=headers, timeout=5).json()
        search_results = r.get('query', {}).get('search', [])
        if not search_results:
            # Try without year as fallback search
            if year:
                search_params['srsearch'] = f"{movie_title} film"
                r = requests.get(search_url, params=search_params, headers=headers, timeout=5).json()
                search_results = r.get('query', {}).get('search', [])
            
            if not search_results:
                return None
            
        page_title = search_results[0]['title']
        
        # 2. Get list of all images on page with continuation
        images = []
        params = {
            'action': 'query',
            'titles': page_title,
            'prop': 'images',
            'format': 'json',
            'imlimit': 'max'
        }
        
        while True:
            r = requests.get(search_url, params=params, headers=headers, timeout=5).json()
            pages = r.get('query', {}).get('pages', {})
            page_id = list(pages.keys())[0]
            page_data = pages[page_id]
            
            if 'images' in page_data:
                images.extend(page_data['images'])
                
            if 'continue' in r:
                params.update(r['continue'])
            else:
                break
        
        # 3. Find the poster image
        poster_file = None
        # Priority 1: Contains 'poster' and is an image extension
        for img in images:
            title = img.get('title', '')
            title_lower = title.lower()
            if 'poster' in title_lower and (title_lower.endswith('.jpg') or title_lower.endswith('.jpeg') or title_lower.endswith('.png')):
                poster_file = title
                break
                
        if not poster_file:
            # Priority 2: First non-svg/commons image
            for img in images:
                title = img.get('title', '')
                title_lower = title.lower()
                if (title_lower.endswith('.jpg') or title_lower.endswith('.jpeg') or title_lower.endswith('.png')):
                    if 'commons-logo' not in title_lower and 'wikidata' not in title_lower and 'icon' not in title_lower:
                        poster_file = title
                        break
                        
        if not poster_file:
            return None
            
        # 4. Get the direct upload CDN URL
        resolve_params = {
            'action': 'query',
            'titles': poster_file,
            'prop': 'imageinfo',
            'iiprop': 'url',
            'format': 'json'
        }
        r = requests.get(search_url, params=resolve_params, headers=headers, timeout=5).json()
        pages = r.get('query', {}).get('pages', {})
        file_id = list(pages.keys())[0]
        info = pages[file_id].get('imageinfo', [])
        if info:
            return info[0].get('url')
            
    except Exception as e:
        print(f"Wikipedia poster search failed for '{movie_title}': {e}")
    
    return None

