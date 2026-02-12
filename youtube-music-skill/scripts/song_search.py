# Song search script for YouTube Music Skill
# Requires ytmusicapi

from ytmusicapi import YTMusic
import sys
import os
import uuid
import shutil
import atexit
from pathlib import Path

# Session-temp utilities — centralized in `playlist_manager.py`
# (keep a single implementation in `playlist_manager.py`; import here to avoid duplication)
from playlist_manager import create_session_tmp, cleanup_session_tmp

# Usage: python song_search.py "song name" ["artist name"]
def search_song(song_name, artist_name=None):
    headers_path = os.environ.get("YTMUSIC_HEADERS")
    if not headers_path:
        print("Error: YTMUSIC_HEADERS environment variable not set.")
        sys.exit(1)
    ytmusic = YTMusic(headers_path)
    query = song_name if not artist_name else f"{song_name} {artist_name}"
    results = ytmusic.search(query, filter="songs")
    for song in results:
        print(f"{song['title']} by {song['artists'][0]['name']} (videoId: {song['videoId']})")

if __name__ == "__main__":
    # create session tmp dir and ensure cleanup on exit
    session_dir = create_session_tmp()
    atexit.register(cleanup_session_tmp, session_dir)
    try:
        if len(sys.argv) < 2:
            print("Usage: python song_search.py 'song name' ['artist name']")
            sys.exit(1)
        song_name = sys.argv[1]
        artist_name = sys.argv[2] if len(sys.argv) > 2 else None
        # example: scripts may create temporary files under os.environ['SESSION_TMP_DIR']
        print(f"Using session tmp dir: {session_dir}")
        search_song(song_name, artist_name)
    finally:
        cleanup_session_tmp(session_dir)
