import os
import sqlite3
import time
from helpers.posters import fetch_poster_by_tmdb_id, fetch_wikipedia_poster

DB_PATH = os.path.join("instance", "movie_app.db")

def populate_database_posters():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Please run app.py first to seed the database.")
        return

    print("Connecting to database...")
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()

    # Find movies with missing posters
    cursor.execute("SELECT id, tmdb_id, title, year FROM movies WHERE poster_path IS NULL")
    movies = cursor.fetchall()
    
    total_movies = len(movies)
    if total_movies == 0:
        print("All movies already have poster URLs populated!")
        conn.close()
        return

    print(f"Found {total_movies} movies with missing posters.")
    print("Fetching poster URLs (TMDB direct lookup first, Wikipedia fallback)...")
    print("Press Ctrl+C to stop at any time. Progress is saved incrementally.\n")

    count = 0
    updated_count = 0
    failed_count = 0
    start_time = time.time()

    try:
        for movie_id, tmdb_id, title, year in movies:
            count += 1
            poster_url = None

            # Strategy 1: Fast TMDB direct lookup by ID (most movies have tmdb_id from CSV)
            if tmdb_id and str(tmdb_id).strip() and str(tmdb_id) != 'nan':
                poster_url = fetch_poster_by_tmdb_id(tmdb_id)

            # Strategy 2: Wikipedia fallback for movies without TMDB ID or failed lookup
            if not poster_url:
                poster_url = fetch_wikipedia_poster(title, year)
            
            if poster_url:
                retries = 5
                while retries > 0:
                    try:
                        cursor.execute("UPDATE movies SET poster_path = ? WHERE id = ?", (poster_url, movie_id))
                        conn.commit()
                        updated_count += 1
                        # Progress bar style output
                        pct = int((count / total_movies) * 100)
                        bar = '█' * (pct // 2) + '░' * (50 - pct // 2)
                        print(f"\r[{bar}] {pct}% ({count}/{total_movies}) ✓ {title[:40]}", end="", flush=True)
                        break
                    except sqlite3.OperationalError as e:
                        if "locked" in str(e).lower():
                            retries -= 1
                            time.sleep(1.0)
                        else:
                            raise e
                if retries == 0:
                    failed_count += 1
                    print(f"\n  ✗ DB locked after 5 retries: '{title}' ({year})")
            else:
                failed_count += 1
                pct = int((count / total_movies) * 100)
                bar = '█' * (pct // 2) + '░' * (50 - pct // 2)
                print(f"\r[{bar}] {pct}% ({count}/{total_movies}) ✗ No poster: {title[:40]}", end="", flush=True)
            
            # Polite delay between API requests
            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Saving progress...")
    
    finally:
        conn.commit()
        conn.close()
        elapsed_time = time.time() - start_time
        print(f"\n\n{'='*55}")
        print(f"  Batch Poster Update Complete")
        print(f"{'='*55}")
        print(f"  Time elapsed:    {elapsed_time:.1f}s")
        print(f"  Total processed: {count}/{total_movies}")
        print(f"  Posters found:   {updated_count}")
        print(f"  Failed/missing:  {failed_count}")
        print(f"{'='*55}")

if __name__ == "__main__":
    populate_database_posters()
