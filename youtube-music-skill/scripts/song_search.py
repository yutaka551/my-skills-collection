# Song search script for YouTube Music Skill
# Requires ytmusicapi

from ytmusicapi import YTMusic
import sys
import os

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
    if len(sys.argv) < 2:
        print("Usage: python song_search.py 'song name' ['artist name']")
        sys.exit(1)
    song_name = sys.argv[1]
    artist_name = sys.argv[2] if len(sys.argv) > 2 else None
    search_song(song_name, artist_name)
