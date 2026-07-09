import os
import sqlite3
import time
import requests
from recommend import fetch_wikipedia_poster

DB_PATH = os.path.join("instance", "movie_app.db")

def populate_database_posters():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Please run app.py first to seed the database.")
        return

    print("Connecting to database...")
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()

    # Find movies with missing posters
    cursor.execute("SELECT id, title, year FROM movies WHERE poster_path IS NULL")
    movies = cursor.fetchall()
    
    total_movies = len(movies)
    if total_movies == 0:
        print("All movies already have poster URLs populated!")
        conn.close()
        return

    print(f"Found {total_movies} movies with missing posters.")
    print("Fetching poster URLs from Wikipedia (this will bypass any TMDB network blocks)...")
    print("Press Ctrl+C to stop at any time.")

    count = 0
    updated_count = 0
    start_time = time.time()

    try:
        for movie_id, title, year in movies:
            count += 1
            # Fetch poster URL from Wikipedia
            poster_url = fetch_wikipedia_poster(title, year)
            
            if poster_url:
                retries = 5
                while retries > 0:
                    try:
                        cursor.execute("UPDATE movies SET poster_path = ? WHERE id = ?", (poster_url, movie_id))
                        conn.commit()
                        updated_count += 1
                        print(f"[{count}/{total_movies}] Success: '{title}' ({year}) -> {poster_url[:75]}...")
                        break
                    except sqlite3.OperationalError as e:
                        if "locked" in str(e).lower():
                            retries -= 1
                            time.sleep(1.0)
                        else:
                            raise e
                if retries == 0:
                    print(f"[{count}/{total_movies}] Write failed (database locked after 5 retries): '{title}' ({year})")
            else:
                print(f"[{count}/{total_movies}] Failed to find poster for: '{title}' ({year})")
            
            # Rate limiting / polite delay
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Saving progress...")
    
    finally:
        conn.commit()
        conn.close()
        elapsed_time = time.time() - start_time
        print("\n==================================================")
        print(f"Batch update completed in {elapsed_time:.1f} seconds.")
        print(f"Total processed: {count}")
        print(f"Successfully populated: {updated_count} posters.")
        print("==================================================")

if __name__ == "__main__":
    populate_database_posters()
