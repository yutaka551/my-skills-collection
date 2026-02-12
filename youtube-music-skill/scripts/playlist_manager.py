# Playlist management script for YouTube Music Skill
# Requires ytmusicapi

from ytmusicapi import YTMusic
import sys
import os
import uuid
import shutil
import atexit
from pathlib import Path

# Session-temp utilities ---------------------------------------------------
def create_session_tmp(session_id=None):
    root = Path(__file__).resolve().parents[2]
    tmp_base = root / "tmp"
    tmp_base.mkdir(parents=True, exist_ok=True)
    sid = session_id or os.environ.get("SESSION_ID") or str(uuid.uuid4())
    session_dir = tmp_base / sid
    session_dir.mkdir(parents=True, exist_ok=True)
    os.environ["SESSION_TMP_DIR"] = str(session_dir)
    return session_dir

def cleanup_session_tmp(session_dir: Path):
    try:
        if session_dir.exists():
            shutil.rmtree(session_dir)
    except Exception as e:
        print(f"Warning: failed to remove session tmp dir {session_dir}: {e}")

# Usage: python playlist_manager.py <action> <playlist_name> [<description>] [<song_name> <artist_name>]
# Actions: create <playlist_name> [<description>], add <playlist_name> <song_name> [<artist_name>], list, get <playlist_id>  
#
# Notes for `create`:
# - If <description> is a URL, the script will fetch the page title and set the playlist description to "<page title> — <URL>".
# - If <description> is non-URL text, it will be used as the playlist description.
# - If omitted or not useful, the playlist description will be empty.
def get_ytmusic():
    headers_path = os.environ.get("YTMUSIC_HEADERS")
    if not headers_path:
        print("Error: YTMUSIC_HEADERS environment variable not set.")
        sys.exit(1)
    return YTMusic(headers_path)


def create_playlist(playlist_name, description=None, privacy="PRIVATE"):
    """Create a playlist.

    privacy: one of 'PRIVATE', 'UNLISTED', 'PUBLIC' (case-insensitive). Defaults to 'PRIVATE'.
    The description argument is used exactly as provided (or empty if None).
    """
    ytmusic = get_ytmusic()
    desc_text = description or ""
    privacy_param = (privacy or "PRIVATE").upper()
    if privacy_param not in ("PRIVATE", "UNLISTED", "PUBLIC"):
        print(f"Invalid privacy '{privacy}'. Falling back to PRIVATE.")
        privacy_param = "PRIVATE"
    playlist_id = ytmusic.create_playlist(playlist_name, desc_text, privacy_status=privacy_param)
    print(f"Playlist '{playlist_name}' created with ID: {playlist_id} (privacy={privacy_param})")

def add_song_to_playlist(playlist_name, song_name, artist_name=None):
    ytmusic = get_ytmusic()
    playlists = ytmusic.get_library_playlists()
    playlist_id = next((pl['playlistId'] for pl in playlists if pl['title'] == playlist_name), None)
    if not playlist_id:
        print(f"Playlist '{playlist_name}' not found.")
        return
    query = song_name if not artist_name else f"{song_name} {artist_name}"
    results = ytmusic.search(query, filter="songs")
    if not results:
        print("Song not found.")
        return
    song_id = results[0]['videoId']
    ytmusic.add_playlist_items(playlist_id, [song_id])
    print(f"Added '{song_name}' to playlist '{playlist_name}'.")

def list_playlists():
    ytmusic = get_ytmusic()
    playlists = ytmusic.get_library_playlists(limit=None)
    for pl in playlists:
        print(f"{pl['title']} (ID: {pl['playlistId']})")

def get_playlist_songs(playlist_id):
    ytmusic = get_ytmusic()
    playlist_data = ytmusic.get_playlist(playlist_id, limit=None)
    songs = playlist_data.get('tracks', [])
    return songs

def remove_song_from_playlist(playlist_name, song_name, artist_name=None):
    ytmusic = get_ytmusic()
    playlists = ytmusic.get_library_playlists()
    playlist_id = next((pl['playlistId'] for pl in playlists if pl['title'] == playlist_name), None)
    if not playlist_id:
        print(f"Playlist '{playlist_name}' not found.")
        return
    playlist_data = ytmusic.get_playlist(playlist_id, limit=None)
    tracks = playlist_data.get('tracks', [])
    query = song_name if not artist_name else f"{song_name} {artist_name}"
    # Find the track to remove
    for track in tracks:
        if track['title'].lower() == song_name.lower():
            if artist_name:
                track_artists = [artist['name'].lower() for artist in track.get('artists', [])]
                if artist_name.lower() in track_artists:
                    # Remove the track
                    videos_to_remove = [{'videoId': track['videoId'], 'setVideoId': track['setVideoId']}]
                    ytmusic.remove_playlist_items(playlist_id, videos_to_remove)
                    print(f"Removed '{song_name}' by {artist_name} from playlist '{playlist_name}'.")
                    return
            else:
                # Remove the track
                videos_to_remove = [{'videoId': track['videoId'], 'setVideoId': track['setVideoId']}]
                ytmusic.remove_playlist_items(playlist_id, videos_to_remove)
                print(f"Removed '{song_name}' from playlist '{playlist_name}'.")
                return
    print(f"Song '{song_name}' not found in playlist '{playlist_name}'.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python playlist_manager.py <action> <playlist_name> [<description>] [<song_name> <artist_name>] [<privacy>]")
        print("Actions: create <playlist_name> [<description>] [<privacy>], add <playlist_name> <song_name> [<artist_name>], remove <playlist_name> <song_name> [<artist_name>], list, get <playlist_id>")
        print("  <privacy> can be: private (default), unlisted, public")
        sys.exit(1)
    action = sys.argv[1]
    if action == "create":
        if len(sys.argv) < 3:
            print("Usage: python playlist_manager.py create <playlist_name> [<description>] [<privacy>]")
            sys.exit(1)
        privacy_arg = sys.argv[4] if len(sys.argv) > 4 else None
        create_playlist(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None, privacy_arg)
    elif action == "add":
        if len(sys.argv) < 4:
            print("Usage: python playlist_manager.py add <playlist_name> <song_name> [<artist_name>]")
            sys.exit(1)
        add_song_to_playlist(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif action == "remove":
        if len(sys.argv) < 4:
            print("Usage: python playlist_manager.py remove <playlist_name> <song_name> [<artist_name>]")
            sys.exit(1)
        remove_song_from_playlist(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif action == "list":
        list_playlists()
    elif action == "get":
        if len(sys.argv) < 3:
            print("Usage: python playlist_manager.py get <playlist_id>")
            sys.exit(1)
        songs = get_playlist_songs(sys.argv[2])
        for song in songs:
            print(f"{song['title']} by {song['artists'][0]['name']}")
    else:
        print("Unknown action.")

if __name__ == "__main__":
    # create session tmp dir and ensure cleanup on exit
    session_dir = create_session_tmp()
    atexit.register(cleanup_session_tmp, session_dir)
    try:
        print(f"Using session tmp dir: {session_dir}")
        main()
    finally:
        cleanup_session_tmp(session_dir)
