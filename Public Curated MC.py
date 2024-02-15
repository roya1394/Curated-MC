import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging

logging.basicConfig(level=logging.INFO)

# Constants for OAuth
CLIENT_ID = 'INSERT YOUR CLIENT ID'
CLIENT_SECRET = 'INSERT YOUR CLIENT SECRET'
REDIRECT_URI = 'http://localhost/'
SCOPE = 'playlist-modify-private user-read-recently-played'

def create_playlist(sp, user_id, playlist_name, track_uris, target_duration_ms):
    logging.info(f"Creating playlist '{playlist_name}'...")
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=False)

    remaining_duration_ms = target_duration_ms

    # Spotify API has a limit on the number of tracks that can be added in a single request
    # Handle pagination to add tracks to the playlist
    for i in range(0, len(track_uris), 100):
        batch = track_uris[i:i + 100]
        batch_duration = sum(sp.track(track)['duration_ms'] for track in batch)

        if batch_duration <= remaining_duration_ms:
            sp.playlist_add_items(playlist_id=playlist['id'], items=batch)
            remaining_duration_ms -= batch_duration
        else:
            logging.warning("Not enough space in the playlist for all tracks.")
            break

    logging.info(f"Playlist '{playlist_name}' created successfully!")
    return playlist['external_urls']['spotify']

def search_tracks(sp, keywords, target_duration_ms, sort_by_popularity=True):
    track_uris = []
    total_duration_ms = 0

    # Increase the limit to get more results
    results = sp.search(q=keywords, type='track', limit=50, market='US')

    # Sort by popularity if specified
    if sort_by_popularity:
        results['tracks']['items'] = sorted(results['tracks']['items'], key=lambda x: x['popularity'], reverse=True)

    while results['tracks']['items'] and total_duration_ms < target_duration_ms:
        for track in results['tracks']['items']:
            if total_duration_ms + track['duration_ms'] <= target_duration_ms:
                track_uris.append(track['uri'])
                total_duration_ms += track['duration_ms']

        if total_duration_ms < target_duration_ms and results['tracks']['next']:
            results = sp.next(results['tracks'])
        else:
            break

    return track_uris

def filter_tracks_for_environment(sp, track_uris, environment):
    # Customize this function based on the environments you want to support
    filtered_tracks = []
    for track_uri in track_uris:
        track_info = sp.track(track_uri)
        track_keywords = ' '.join([artist['name'].lower() for artist in track_info['artists']] +
                                  [track_info['name'].lower()])
        if environment in track_keywords:
            filtered_tracks.append(track_uri)
    return filtered_tracks

def get_recent_tracks(sp, limit=50):
    logging.info("Fetching recently played tracks...")
    results = sp.current_user_recently_played(limit=limit)
    return [item['track']['uri'] for item in results['items']]

def search_tracks(sp, keywords, target_duration_ms):
    logging.info(f"Searching for tracks with keywords: {keywords}")
    track_uris = []
    total_duration_ms = 0

    results = sp.search(q=keywords, type='track', limit=50)  # Increase the limit to 50

    while results['tracks']['items'] and total_duration_ms < target_duration_ms:
        for track in results['tracks']['items']:
            if total_duration_ms + track['duration_ms'] <= target_duration_ms:
                track_uris.append(track['uri'])
                total_duration_ms += track['duration_ms']

        if total_duration_ms < target_duration_ms and results['tracks']['next']:
            results = sp.next(results['tracks'])
        else:
            break

    logging.info(f"Found {len(track_uris)} tracks.")
    return track_uris

def filter_recent_tracks(recent_track_uris, keywords):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                                                   redirect_uri=REDIRECT_URI, scope=SCOPE))
    filtered_tracks = []

    for track_uri in recent_track_uris:
        track_info = sp.track(track_uri)
        track_keywords = ' '.join([artist['name'].lower() for artist in track_info['artists']] +
                                  [track_info['name'].lower()])
        if any(keyword in track_keywords for keyword in keywords.split()):
            filtered_tracks.append(track_uri)

    return filtered_tracks

def search_tracks_for_environment(sp, environment):
    # Customize this function based on the environments you want to support
    if environment == "gym":
        return search_tracks(sp, "energetic workout", float('inf'))
    elif environment == "study":
        return search_tracks(sp, "calm focus", float('inf'))
    elif environment == "late night drive":
        return search_tracks(sp, "chill drive", float('inf'))
    elif environment == "bedroom":
        return search_tracks(sp, "relaxing bedroom", float('inf'))
    elif environment == "shower":
        return search_tracks(sp, "uplifting shower", float('inf'))
    elif environment == "dinner party":
        return search_tracks(sp, "dinner party", float('inf'))
    elif environment == "road trip":
        return search_tracks(sp, "road trip", float('inf'))
    elif environment == "crying":
        return search_tracks(sp, "sad songs", float('inf'))
    else:
        # Default to a general search if the environment is not recognized
        return search_tracks(sp, "relaxing", float('inf'))

def convert_minutes_to_milliseconds(minutes):
    return int(minutes) * 60 * 1000

def main():
    # Set up authentication
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                                                   redirect_uri=REDIRECT_URI, scope=SCOPE))

    try:
        # Get the current user's ID
        user_id = sp.current_user()['id']

        # Get user input for playlist keywords, duration, and custom playlist name
        mood = input("Enter mood keywords (e.g., happy, relaxed): ").strip().lower()
        genre = input("Enter genre keywords (e.g., pop, rock): ").strip().lower()
        artist = input("Enter artist name: ").strip().lower()
        duration = input("Enter playlist duration in minutes: ").strip().lower()
        custom_playlist_name = input("Enter a custom name for your playlist (press Enter for default): ").strip()

        # Combine keywords for the main search
        main_keywords = f'{mood or ""} {genre or ""} {artist or ""}'

        # Get tracks from recent history
        recent_track_uris = get_recent_tracks(sp)

        # Filter recent tracks based on main keywords
        filtered_recent_tracks = filter_recent_tracks(recent_track_uris, main_keywords)

        # Get tracks based on user-inputted keywords with sorting by popularity
        if duration:
            target_duration_ms = convert_minutes_to_milliseconds(duration)
            keyword_track_uris = search_tracks(sp, main_keywords, target_duration_ms)
        else:
            keyword_track_uris = search_tracks(sp, main_keywords, float('inf'))

        # Sort keyword tracks by popularity
        keyword_track_uris = sorted(keyword_track_uris, key=lambda uri: sp.track(uri)['popularity'], reverse=True)

        # Combine filtered recent tracks and keyword search tracks
        track_uris = filtered_recent_tracks + keyword_track_uris

        if not track_uris:
            print("No tracks found. Please refine your search or listen to more music.")
            return

        # Ensure the total duration of the playlist matches the target duration
        actual_duration_ms = sum(sp.track(track)['duration_ms'] for track in track_uris)
        if actual_duration_ms > target_duration_ms:
            print(f"Warning: The playlist duration exceeds the specified duration by "
                  f"{(actual_duration_ms - target_duration_ms) / 1000} seconds.")

        # Create a playlist based on the combined tracks
        default_playlist_name = "Combined Playlist"
        playlist_name = custom_playlist_name or default_playlist_name
        playlist_url = create_playlist(sp, user_id, playlist_name, track_uris, target_duration_ms)

        print(f"Playlist created successfully! You can listen to it here: {playlist_url}")

    except spotipy.SpotifyException as e:
        print(f"Spotify API error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
